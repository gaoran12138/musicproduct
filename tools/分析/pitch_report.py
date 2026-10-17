#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""音准可视化报告：pyin 提取音高 -> 音符切分 -> 音分误差统计 -> PNG 图

用法（走 .venv-as）：
    python pitch_report.py <wav> [--label 分裂翻唱] [--png out.png] [--json out.json]

产出：
    * PNG 三联图（音高轨迹 / 音分误差分布 / 分区准确率）
    * 控制台摘要 + 可选 JSON

约定：
    * 音分误差 = 相对"自身调音基准（中位数）"的偏差，避免整体偏高/偏低被误判
    * 只有时长 >= MIN_NOTE 的音符参与统计
"""
import argparse
import json
import os
import sys

import numpy as np

try:
    import librosa
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:  # pragma: no cover
    print(f"[!!] 依赖缺失：{e}", file=sys.stderr)
    sys.exit(2)

SR = 22050
MIN_NOTE = 0.09          # 最短音符
FMIN, FMAX = 82.0, 1050.0  # E2..C6
BG = (250, 248, 244)
INK = (42, 40, 38)
GRID = (222, 216, 206)
ACC = (61, 90, 128)
WARN = (179, 74, 50)
GOOD = (74, 124, 89)
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def font(size):
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def load_mono(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    return y


def track(y):
    f0, vflag, vprob = librosa.pyin(
        y, fmin=FMIN, fmax=FMAX, sr=SR, frame_length=2048, hop_length=256,
        fill_na=np.nan, center=True)
    times = librosa.times_like(f0, sr=SR, hop_length=256)
    return times, f0, vflag, vprob


def notes_from(times, f0, min_dur=MIN_NOTE):
    """把逐帧频率切成稳定音符（半音内允许 ±70 音分抖动）。"""
    midi = 69 + 12 * np.log2(f0 / 440.0)
    notes = []
    cur = None
    for t, m in zip(times, midi):
        if not np.isfinite(m):
            if cur:
                notes.append(cur)
                cur = None
            continue
        r = int(round(m))
        if cur is None:
            cur = {"midi": r, "t0": t, "t1": t, "vals": [m]}
        elif abs(m - cur["midi"]) <= 0.70:
            cur["t1"] = t
            cur["vals"].append(m)
        else:
            notes.append(cur)
            cur = {"midi": r, "t0": t, "t1": t, "vals": [m]}
    if cur:
        notes.append(cur)

    out = []
    for n in notes:
        dur = n["t1"] - n["t0"]
        if dur < min_dur:
            continue
        v = np.array(n["vals"])
        # 去掉音符两端的滑音（各 20%）
        k = max(1, int(len(v) * 0.2))
        core = v[k: len(v) - k] if len(v) > 2 * k else v
        out.append({
            "start": float(n["t0"]), "dur": float(dur),
            "midi": int(round(np.median(core))),
            "cents_raw": float((np.median(core) - round(np.median(midi_of(core)))) * 100),
            "freq": float(2 ** ((np.median(core) - 69) / 12) * 440),
        })
    return out


def midi_of(vals):
    return np.array(vals)


def analyze(y):
    times, f0, vflag, vprob = track(y)
    midi = 69 + 12 * np.log2(np.where(np.isfinite(f0), f0, np.nan) / 440.0)
    notes = notes_from(times, f0)
    if not notes:
        return None
    # 全局调音基准（音分中位数）
    allc = []
    for n in notes:
        # 与最近整半音的偏差
        m = 69 + 12 * np.log2(n["freq"] / 440.0)
        allc.append((m - round(m)) * 100)
    allc = np.array(allc)
    tuning = float(np.median(allc))
    for n in notes:
        m = 69 + 12 * np.log2(n["freq"] / 440.0)
        n["cents"] = float((m - round(m)) * 100 - tuning)
    cents = np.array([n["cents"] for n in notes])
    abs_c = np.abs(cents)
    midis = np.array([n["midi"] for n in notes])
    durs = np.array([n["dur"] for n in notes])

    # 声区划分（以用户《分裂》实测换声点 F#4=66 / G#4=68 为界）
    def zone(m):
        if m < 60:      # C4
            return "低音区 <C4"
        if m <= 64:     # E4
            return "中音区 C4-E4"
        if m <= 68:
            return "换声区 F4-G#4"
        return "高音区 >G#4"

    zones = {}
    for m, c, d in zip(midis, cents, durs):
        z = zone(m)
        zones.setdefault(z, []).append((c, d))

    stats = {
        "notes": int(len(notes)),
        "duration": float(times[-1]),
        "range_low": f"{NOTE_NAMES[int(midis.min()) % 12]}{int(midis.min()) // 12 - 1}",
        "range_high": f"{NOTE_NAMES[int(midis.max()) % 12]}{int(midis.max()) // 12 - 1}",
        "range_semitones": int(midis.max() - midis.min()),
        "tuning_cents": round(tuning, 1),
        "median_abs_cents": round(float(np.median(abs_c)), 1),
        "mean_abs_cents": round(float(np.mean(abs_c)), 1),
        "pct_25": round(float(np.mean(abs_c <= 25) * 100), 1),
        "pct_50": round(float(np.mean(abs_c <= 50) * 100), 1),
        "long_notes": {"count": int(np.sum(durs >= 0.6)),
                       "median_cents": round(float(np.median(np.abs(cents[durs >= 0.6]))), 1)
                       if np.any(durs >= 0.6) else None},
        "short_notes": {"count": int(np.sum(durs < 0.6)),
                        "median_cents": round(float(np.median(np.abs(cents[durs < 0.6]))), 1)
                        if np.any(durs < 0.6) else None},
        "zones": {},
    }
    for z, rows in zones.items():
        c = np.array([r[0] for r in rows])
        stats["zones"][z] = {"count": len(rows),
                             "median_abs_cents": round(float(np.median(np.abs(c))), 1),
                             "pct_25": round(float(np.mean(np.abs(c) <= 25) * 100), 1)}
    return {"times": times, "midi": midi, "notes": notes, "cents": cents,
            "stats": stats, "tuning": tuning}


# ------------------------------------------------------------------ 绘图
def draw(res, label, out_png, W=1680, H=1180):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title, f_sub, f_txt, f_small = font(38), font(21), font(17), font(15)

    d.text((60, 40), f"音准报告 · {label}", font=f_title, fill=INK)
    st = res["stats"]
    d.text((62, 94), f"{st['notes']} 个稳定音符 · 时长 {st['duration']:.0f}s · "
                     f"音域 {st['range_low']}-{st['range_high']}（{st['range_semitones']} 半音） · "
                     f"调音基准 {st['tuning_cents']:+.1f} 音分", font=f_sub, fill=(110, 104, 96))

    # ---- 面板 1：音高轨迹（左，宽）
    x0, y0, pw, ph = 60, 150, 1000, 420
    d.rectangle([x0, y0, x0 + pw, y0 + ph], fill=(255, 255, 255), outline=GRID, width=2)
    midi = res["midi"]
    ok = np.isfinite(midi)
    if np.any(ok):
        mlo, mhi = int(np.nanpercentile(midi[ok], 1)) - 1, int(np.nanpercentile(midi[ok], 99)) + 1
        dur = res["stats"]["duration"] or 1
        for m in range(mlo, mhi + 1):
            yy = y0 + ph - (m - mlo) / max(1, (mhi - mlo)) * ph
            d.line([x0, yy, x0 + pw, yy], fill=GRID)
            d.text((x0 + pw + 8, yy - 9), f"{NOTE_NAMES[m % 12]}{m // 12 - 1}", font=f_small, fill=(150, 144, 136))
        for t, m in zip(res["times"], midi):
            if not np.isfinite(m):
                continue
            xx = x0 + (t / dur) * pw
            yy = y0 + ph - (m - mlo) / max(1, (mhi - mlo)) * ph
            d.ellipse([xx - 2.5, yy - 2.5, xx + 2.5, yy + 2.5], fill=ACC)
        for i in range(0, int(dur) + 1, max(1, int(dur // 8))):
            xx = x0 + (i / dur) * pw
            d.line([xx, y0 + ph, xx, y0 + ph + 6], fill=INK)
            d.text((xx - 12, y0 + ph + 10), f"{i // 60}:{i % 60:02d}", font=f_small, fill=(130, 124, 116))
    d.text((x0, y0 - 26), "音高轨迹（像素点=有声帧，横轴时间，纵轴音高）", font=f_txt, fill=INK)

    # ---- 面板 2：音分误差直方图（右上）
    hx, hy, hw, hh = 1120, 150, 500, 420
    d.rectangle([hx, hy, hx + hw, hy + hh], fill=(255, 255, 255), outline=GRID, width=2)
    cents = res["cents"]
    bins = np.arange(-60, 61, 10)
    hist, _ = np.histogram(cents, bins=bins)
    mx = max(1, hist.max())
    for i, h in enumerate(hist):
        bh = h / mx * (hh - 70)
        bx0 = hx + 20 + i * ((hw - 40) / len(hist))
        bw = (hw - 40) / len(hist) - 6
        color = GOOD if abs((bins[i] + bins[i + 1]) / 2) <= 25 else (WARN if abs((bins[i] + bins[i + 1]) / 2) > 40 else (217, 169, 59))
        d.rectangle([bx0, hy + hh - 30 - bh, bx0 + bw, hy + hh - 30], fill=color)
    d.line([hx + hw / 2, hy + 12, hx + hw / 2, hy + hh - 30], fill=(200, 120, 120), width=2)
    d.text((hx, hy - 26), "音分误差分布（绿=±25内 黄=25-40 红=>40）", font=f_txt, fill=INK)
    d.text((hx + 14, hy + hh - 24), f"中位 {st['median_abs_cents']} 音分 · ±25内 {st['pct_25']}%",
           font=f_small, fill=(120, 114, 106))

    # ---- 面板 3：分区准确率（右下）
    zx, zy, zw = 1120, 660, 500
    d.text((zx, zy - 26), "分声区准确率（中位音分，越短越好）", font=f_txt, fill=INK)
    d.rectangle([zx, zy, zx + zw, zy + 380], fill=(255, 255, 255), outline=GRID, width=2)
    zs = sorted(res["stats"]["zones"].items(), key=lambda kv: kv[1]["median_abs_cents"])
    y = zy + 24
    for name, z in zs:
        v = z["median_abs_cents"]
        barw = min(300, v / 60 * 300)
        color = GOOD if v <= 20 else (217, 169, 59) if v <= 30 else WARN
        d.text((zx + 18, y), name, font=f_small, fill=INK)
        d.rectangle([zx + 180, y + 2, zx + 180 + barw, y + 20], fill=color)
        d.text((zx + 190 + barw, y), f"{v:.1f} 音分 ({z['count']})", font=f_small, fill=(120, 114, 106))
        y += 46

    # ---- 底部结论文本
    tx, ty = 60, 700
    lines = [
        f"稳定音符 {st['notes']} 个（长音 {st['long_notes']['count']}，中位 {st['long_notes']['median_cents']} 音分；"
        f"短音 {st['short_notes']['count']}，中位 {st['short_notes']['median_cents']} 音分）",
        f"整体：中位 {st['median_abs_cents']} 音分 · ±25 内 {st['pct_25']}% · ±50 内 {st['pct_50']}%",
        "判定：≤20 优秀 · 20-30 良好（业余歌手常见） · 30-40 需练 · >40 音准不稳",
    ]
    for ln in lines:
        d.text((tx, ty), ln, font=f_txt, fill=INK)
        ty += 32
    d.text((tx, ty + 6), "提示：误差是相对你自己调音基准的偏差；整体偏高/偏低不影响此图（会算进调音基准）",
           font=f_small, fill=(130, 124, 116))

    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    img.save(out_png)
    return out_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--label", default=None)
    ap.add_argument("--png")
    ap.add_argument("--json")
    args = ap.parse_args()

    label = args.label or os.path.splitext(os.path.basename(args.audio))[0]
    y = load_mono(args.audio)
    if len(y) < SR // 2:
        print("[!!] 音频太短", file=sys.stderr)
        return 2
    res = analyze(y)
    if not res:
        print("[!!] 未检测到有效音符", file=sys.stderr)
        return 2
    st = res["stats"]

    print("=" * 62)
    print(f"  音准报告 · {label}")
    print("=" * 62)
    print(f"  音符 {st['notes']} 个 · 时长 {st['duration']:.1f}s · 音域 {st['range_low']}-{st['range_high']}"
          f"（{st['range_semitones']} 半音）")
    print(f"  调音基准 {st['tuning_cents']:+.1f} 音分（整体偏高/偏低）")
    print(f"  音准：中位 {st['median_abs_cents']} · 平均 {st['mean_abs_cents']} 音分"
          f" · ±25 内 {st['pct_25']}% · ±50 内 {st['pct_50']}%")
    if st["long_notes"]["median_cents"] is not None:
        print(f"  长音 {st['long_notes']['count']} 个 中位 {st['long_notes']['median_cents']} 音分"
              f" | 短音 {st['short_notes']['count']} 个 中位 {st['short_notes']['median_cents']} 音分")
    for z, v in sorted(st["zones"].items()):
        print(f"    {z:<14} {v['count']:>3} 音符  中位 {v['median_abs_cents']:>5} 音分  ±25内 {v['pct_25']}%")

    png = args.png or os.path.join("档案", "报告", f"{label}_音准.png")
    out = draw(res, label, png)
    print(f"\n  PNG -> {out}")

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        payload = {"label": label, "audio": args.audio, **st,
                   "notes_detail": [{k: round(v, 3) if isinstance(v, float) else v for k, v in n.items()}
                                    for n in res["notes"]]}
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  json -> {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
