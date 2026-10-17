#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""和弦识别：chroma 模板打分 + Viterbi 平滑 + 转位（slash chord）判定

用法（走 .venv-as）：
    python chords.py <audio> [--srt out.srt] [--json out.json] [--bpm 70]
                     [--no-viterbi] [--capo 0]

输出：
    * 控制台时间轴（小节/时间/和弦/置信度）
    * SRT 字幕（可直接喂给 music render --srt 叠加和弦）
    * JSON（分段 + 每段候选）

原理：
    1. librosa.effects.harmonic 去掉打击乐 -> chroma_cqt 取 12 维音级能量
    2. 每个模板（根音 × 和弦类型）做加权余弦打分
    3. 以节拍为状态序列，用 HMM + Viterbi 平滑（相邻和弦有切换惩罚）
    4. 低音区（C1-C3）chroma 峰值 != 根音 时判成转位 X/Y
"""
import argparse
import json
import os
import sys

import numpy as np

try:
    import librosa
except Exception as e:  # pragma: no cover
    print(f"[!!] 需要 librosa: {e}", file=sys.stderr)
    sys.exit(2)

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# 和弦类型：音程（相对根音）与权重
QUALITIES = {
    "": [(0, 1.00), (4, 0.92), (7, 0.85)],
    "m": [(0, 1.00), (3, 0.92), (7, 0.85)],
    "7": [(0, 1.00), (4, 0.90), (7, 0.80), (10, 0.85)],
    "maj7": [(0, 1.00), (4, 0.90), (7, 0.80), (11, 0.85)],
    "m7": [(0, 1.00), (3, 0.90), (7, 0.80), (10, 0.85)],
    "sus4": [(0, 1.00), (5, 0.92), (7, 0.88)],
    "sus2": [(0, 1.00), (2, 0.90), (7, 0.88)],
    "dim": [(0, 1.00), (3, 0.90), (6, 0.88)],
    "aug": [(0, 1.00), (4, 0.90), (8, 0.88)],
    "6": [(0, 1.00), (4, 0.90), (7, 0.80), (9, 0.82)],
    "m6": [(0, 1.00), (3, 0.90), (7, 0.80), (9, 0.82)],
    "add9": [(0, 1.00), (4, 0.90), (7, 0.82), (2, 0.80)],
    "9": [(0, 1.00), (4, 0.88), (7, 0.76), (10, 0.84), (2, 0.72)],
    "m9": [(0, 1.00), (3, 0.88), (7, 0.76), (10, 0.84), (2, 0.72)],
    "m7b5": [(0, 1.00), (3, 0.90), (6, 0.88), (10, 0.84)],
    "5": [(0, 1.00), (7, 0.90)],
}

# 转位/挂低音只在"低音是调内非根音"时才出现，以下类型允许
SLASH_OK = {"", "m", "7", "maj7", "m7", "sus4", "sus2", "add9", "6", "m6"}


def build_templates():
    tmpl, labels = [], []
    for root in range(12):
        for q, tones in QUALITIES.items():
            v = np.zeros(12)
            for interval, w in tones:
                v[(root + interval) % 12] = w
            tmpl.append(v / np.linalg.norm(v))
            labels.append(NAMES[root] + q)
    return np.array(tmpl), labels


def segment_chroma(y, sr, bpm=None):
    """返回 (段中心时间, 段 chroma, 段低音 chroma, 段时长)。"""
    harm = librosa.effects.harmonic(y, margin=3.0)
    hop = 512
    chroma = librosa.feature.chroma_cqt(y=harm, sr=sr, hop_length=hop, bins_per_octave=36)
    low = librosa.feature.chroma_cqt(y=harm, sr=sr, hop_length=hop, bins_per_octave=36,
                                     fmin=librosa.note_to_hz("C1"))
    times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=hop)

    onset_env = librosa.onset.onset_strength(y=harm, sr=sr, hop_length=hop)
    if bpm:
        beats = np.array(librosa.beat.beat_track(onset_envelope=onset_env, sr=sr,
                                                 hop_length=hop, start_bpm=bpm)[1])
    else:
        beats = np.array(librosa.beat.beat_track(onset_envelope=onset_env, sr=sr,
                                                 hop_length=hop)[1])
    if len(beats) < 4:  # 节拍检测失败 -> 固定 0.5s
        beats = np.arange(0, chroma.shape[1], max(1, int(0.5 * sr / hop)))
    # 去掉过近的拍点
    keep = [beats[0]]
    for b in beats[1:]:
        if (b - keep[-1]) * hop / sr >= 0.25:
            keep.append(b)
    beats = np.array(keep)
    edges = np.concatenate([[0], beats[1:], [chroma.shape[1]]]).astype(int)
    edges = np.unique(np.clip(edges, 0, chroma.shape[1]))

    out = []
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]
        if b <= a:
            continue
        seg = chroma[:, a:b].mean(axis=1)
        seg_low = low[:, a:b].mean(axis=1)
        dur = (b - a) * hop / sr
        if dur < 0.22:
            continue
        out.append(((times[a] + times[min(b, len(times) - 1)]) / 2.0, seg, seg_low, a, b, dur))
    return out


def viterbi(scores, self_bias=0.10, switch_penalty=0.10):
    """scores: (T, S) 归一化得分。返回状态序列。"""
    T, S = scores.shape
    if T == 0:
        return []
    logp = np.log(np.clip(scores, 1e-6, 1.0))
    dp = np.zeros((T, S))
    bp = np.zeros((T, S), dtype=int)
    dp[0] = logp[0]
    for t in range(1, T):
        prev = dp[t - 1]
        stay = prev + self_bias
        best_other = int(np.argmax(prev))
        trans = prev[best_other] - switch_penalty
        cand = np.full(S, trans)
        cand[best_other] = stay[best_other]
        # 精确写法：每个状态取 max(自身停留, 从最优其他状态切换)
        take_stay = stay >= cand
        dp[t] = logp[t] + np.where(take_stay, stay, cand)
        bp[t] = np.where(take_stay, np.arange(S), best_other)
    path = [int(np.argmax(dp[-1]))]
    for t in range(T - 1, 0, -1):
        path.append(int(bp[t][path[-1]]))
    return path[::-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--srt", help="输出和弦 SRT")
    ap.add_argument("--json", help="输出 json")
    ap.add_argument("--bpm", type=float, help="固定 BPM（节拍跟踪不稳时用）")
    ap.add_argument("--capo", type=int, default=0, help="移调半音（如夹 2 品填 -2 得到手位和弦）")
    ap.add_argument("--no-viterbi", action="store_true", help="不做平滑，逐段取最高分")
    ap.add_argument("--min-dur", dest="min_dur", type=float, default=0.35,
                    help="最短和弦时长（默认 0.35s）")
    args = ap.parse_args()

    sr = 22050
    y, _ = librosa.load(args.audio, sr=sr, mono=True)
    if len(y) == 0:
        print("[!!] 空音频", file=sys.stderr)
        return 2
    segs = segment_chroma(y, sr, args.bpm)
    if not segs:
        print("[!!] 分段为空", file=sys.stderr)
        return 2

    tmpl, labels = build_templates()
    scores = []
    for _, seg, *_ in segs:
        v = seg / (np.linalg.norm(seg) + 1e-9)
        scores.append(tmpl @ v)
    scores = np.clip(np.array(scores), 0, 1)
    # 质量偏好：中文流行少用强力和弦，主/小三优先；极端和弦扣分
    qb = {"": 0.025, "m": 0.02, "7": 0.012, "m7": 0.012, "maj7": 0.012,
          "5": -0.045, "aug": -0.02, "dim": -0.02, "m7b5": -0.012, "m6": -0.008}
    bias = np.zeros(len(labels))
    for i, lb in enumerate(labels):
        q = lb[2:] if len(lb) > 1 and lb[1] == "#" else lb[1:]
        bias[i] = qb.get(q, 0.0)
    scores = np.clip(np.array(scores) + bias, 0, 1)
    idx = list(range(len(labels))) if args.no_viterbi else viterbi(scores)
    if args.no_viterbi:
        idx = [int(np.argmax(s)) for s in scores]

    rows = []
    for k, (seg, score_row) in enumerate(zip(segs, scores)):
        t, seg_chroma, seg_low, a, b, dur = seg
        st = int(idx[k])
        label = labels[st]
        conf = float(score_row[st])
        # 转位判定：低音区峰值
        base_pc = int(np.argmax(seg_low))
        # 从 label 反解根音
        for pc in range(12):
            if label.startswith(NAMES[pc]) and (len(NAMES[pc]) == 1 or label[1] == "#"):
                root_pc = pc
                break
        quality = label[len(NAMES[root_pc]):]
        if args.capo:
            root_pc = (root_pc - args.capo) % 12
            label = NAMES[root_pc] + quality
        if (quality in SLASH_OK and base_pc != root_pc
                and seg_low[base_pc] > 1.15 * np.mean(seg_low)):
            label = f"{label}/{NAMES[base_pc]}"
        # 时间
        start = t - dur / 2.0
        rows.append({"start": max(0.0, start), "dur": dur, "chord": label,
                     "conf": conf, "beat_a": int(a), "beat_b": int(b)})

    # 合并相邻同和弦
    merged = []
    for r in rows:
        if merged and merged[-1]["chord"] == r["chord"] and \
                abs((merged[-1]["start"] + merged[-1]["dur"]) - r["start"]) < 0.05:
            merged[-1]["dur"] += r["dur"]
            merged[-1]["conf"] = max(merged[-1]["conf"], r["conf"])
            merged[-1]["beat_b"] = r["beat_b"]
        elif r["dur"] >= args.min_dur:
            merged.append(dict(r))
    # 短碎片并入前一个
    final = []
    for r in merged:
        if final and r["dur"] < args.min_dur:
            final[-1]["dur"] += r["dur"]
        else:
            final.append(r)

    if not final:
        print("[!!] 无有效和弦段", file=sys.stderr)
        return 2

    print("=" * 70)
    print(f"  和弦识别 · {args.audio}")
    print("=" * 70)
    print(f"  分段 {len(final)} 个 | 平均置信度 {np.mean([r['conf'] for r in final]):.3f}")
    print()
    bar = 1
    prev_beat = None
    for r in final:
        if prev_beat is not None and r["beat_a"] - prev_beat >= 4:
            bar += 1
        prev_beat = r["beat_b"]
        mm, ss = divmod(r["start"], 60)
        print(f"  {int(mm):02d}:{ss:05.2f}  +{r['dur']:5.2f}s  {r['chord']:<10} {r['conf']:.2f}")

    payload = {
        "audio": args.audio,
        "segments": [{"start": round(r["start"], 3), "duration": round(r["dur"], 3),
                      "chord": r["chord"], "confidence": round(r["conf"], 4)} for r in final],
    }
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n  json -> {args.json}")

    if args.srt:
        os.makedirs(os.path.dirname(os.path.abspath(args.srt)), exist_ok=True)

        def ts(sec):
            h = int(sec // 3600)
            m = int(sec % 3600 // 60)
            s = sec % 60
            return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

        lines = []
        for i, r in enumerate(final, 1):
            end = r["start"] + r["dur"]
            lines += [str(i), f"{ts(r['start'])} --> {ts(end)}", r["chord"], ""]
        with open(args.srt, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(lines))
        print(f"  srt  -> {args.srt}（{len(final)} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
