#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""离线歌词识别（faster-whisper）：无歌词源时兜底生成带时间轴的 SRT/LRC

用法（走 .venv-as）：
    python asr_lrc.py <audio> --srt out.srt [--lrc out.lrc] [--model small]
                            [--device auto] [--lang zh] [--vocal-stem]

说明：
    * device=auto 有 CUDA 用 cuda/float16，否则 cpu/int8
    * 需要 HF_ENDPOINT=https://hf-mirror.com（国内直连 huggingface.co 常不通）
    * --vocal-stem 会先做中置声道提取（人声在中间，压掉两侧伴奏能量），提升识别率
"""
import argparse
import os
import subprocess
import sys
import tempfile
import wave

SR = 16000


def ffmpeg_to_wav(src, dst, vocal_stem=False):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src]
    if vocal_stem:
        # 中置提取：L-R 相减后再混回单声道，明显削弱居中以外的人声/伴奏
        cmd += ["-af", "pan=mono|c0=0.5*c0-0.5*c1"]
    cmd += ["-ac", "1", "-ar", str(SR), dst]
    subprocess.run(cmd, check=True)
    return dst


def wav_duration(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def ts_srt(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def ts_lrc(t):
    m, s = divmod(t, 60)
    return f"[{int(m):02d}:{s:05.2f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--lrc")
    ap.add_argument("--model", default="small")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--vocal-stem", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.audio):
        print(f"[!!] 找不到 {args.audio}", file=sys.stderr)
        return 2

    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        print(f"[!!] faster-whisper 未安装：{e}", file=sys.stderr)
        return 2

    tmp = tempfile.mkdtemp(prefix="asr_")
    wav = os.path.join(tmp, "in.wav")
    ffmpeg_to_wav(args.audio, wav, args.vocal_stem)
    dur = wav_duration(wav)
    print(f"  音频 {dur:.1f}s -> {args.model} 识别中…")

    device = args.device
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    compute = "float16" if device == "cuda" else "int8"

    def _run(dev, comp):
        m = WhisperModel(args.model, device=dev, compute_type=comp)
        segs, inf = m.transcribe(
            wav, language=args.lang, beam_size=5, vad_filter=True,
            condition_on_previous_text=False,
            vad_parameters={"min_silence_duration_ms": 350})
        rows = []
        for seg in segs:
            text = (seg.text or "").strip()
            if text:
                rows.append((max(0.0, seg.start), min(dur, seg.end), text))
        return rows, inf

    try:
        rows, info = _run(device, compute)
    except Exception as e:
        if device == "cpu":
            print(f"[!!] 识别失败：{e}", file=sys.stderr)
            return 2
        warn = f"  CUDA 不可用（{str(e)[:80]}），回退 CPU int8"
        print(warn)
        device, compute = "cpu", "int8"
        try:
            rows, info = _run(device, compute)
        except Exception as e2:
            print(f"[!!] CPU 也失败：{e2}", file=sys.stderr)
            return 2

    if not rows:
        print("[!!] 未识别到人声", file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(os.path.abspath(args.srt)), exist_ok=True)
    lines = []
    for i, (a, b, t) in enumerate(rows, 1):
        lines += [str(i), f"{ts_srt(a)} --> {ts_srt(b)}", t, ""]
    with open(args.srt, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
    print(f"  SRT  {len(rows)} 条 -> {args.srt}")

    if args.lrc:
        os.makedirs(os.path.dirname(os.path.abspath(args.lrc)), exist_ok=True)
        with open(args.lrc, "w", encoding="utf-8") as f:
            f.write(f"[ti:{os.path.splitext(os.path.basename(args.audio))[0]}]\n")
            for a, b, t in rows:
                f.write(f"{ts_lrc(a)}{t}\n")
        print(f"  LRC  -> {args.lrc}")

    print(f"  语言 {info.language} (p={info.language_probability:.2f}) | 设备 {device}/{compute}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
