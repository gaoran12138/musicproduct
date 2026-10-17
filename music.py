#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""music.py — D:\\musicProduct 统一入口

把散落在 tools\\ 下的脚本收成一个命令。

子命令
  doctor    环境自检（解释器/CUDA/ffmpeg/模型/依赖）
  separate  spleeter 分离 2/4/5 轨（GPU）
  uvr       audio-separator 高质量分离（BS-Roformer / Karaoke / demucs6）
  lyrics    lrclib 抓歌词 -> .lrc + .srt
  ass       srt -> ass（标准/浅底两套样式）
  render    封面 + 歌词 -> mp4（NVENC）
  analyze   演唱声学分析（音域/音准/颤音/换声点）
  freeze    重新生成两套环境的 requirements.txt
  info      显示路径与版本配置

示例
  music doctor
  music separate "素材\\陈绮贞 - 吉他手.flac" -p 5stems
  music uvr "素材\\周杰伦 - 晴天.flac" -m bs
  music lyrics "素材\\陈绮贞 - 吉他手.flac"
  music ass "字幕\\陈绮贞 - 吉他手_歌词.srt"
  music render "素材\\陈绮贞 - 吉他手.flac" --srt "字幕\\陈绮贞 - 吉他手_歌词.srt" --cover "素材\\图片\\吉他手.webp"
  music analyze "素材\\录音34.m4a"
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VERSION = "1.0"

# ---------------------------------------------------------------- 路径配置
ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools"
PY_MAIN = TOOLS / "python310" / "python.exe"
PY_AS = ROOT / ".venv-as" / "Scripts" / "python.exe"
AUDIO_SEP = ROOT / ".venv-as" / "Scripts" / "audio-separator.exe"
FFMPEG_BIN = TOOLS / "ffmpeg" / "bin"
FFMPEG = FFMPEG_BIN / "ffmpeg.exe"
FFPROBE = FFMPEG_BIN / "ffprobe.exe"
CUDA_BIN = TOOLS / "cuda" / "bin"
MODELS = ROOT / "pretrained_models"
UVR_MODELS = Path("D:/tmp/audio-separator-models")

DIR_STEMS = ROOT / "分轨"
DIR_OUT = ROOT / "成品"
DIR_SUB = ROOT / "字幕"
DIR_MEDIA = ROOT / "素材"
DIR_TMP = DIR_MEDIA / "转换中间"
DIR_DOC = ROOT / "文档"
DIR_TAB = ROOT / "吉他谱"
SCRIPT_SUB = TOOLS / "字幕"
SCRIPT_ANA = TOOLS / "分析"

UVR_SHORTCUTS = {
    "bs": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "bsroformer": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "clean": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "karaoke": "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
    "melband": "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
    "demucs6": "htdemucs_6s.yaml",
    "6s": "htdemucs_6s.yaml",
}

AUDIO_EXT = {".flac", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".aiff", ".aif"}


# ---------------------------------------------------------------- 通用工具
def build_env():
    env = dict(os.environ)
    env["PATH"] = ";".join([str(FFMPEG_BIN), str(CUDA_BIN), env.get("PATH", "")])
    env["MODEL_PATH"] = str(MODELS)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def hr(title=""):
    if title:
        print("\n" + "=" * 68)
        print(f"  {title}")
        print("=" * 68)
    else:
        print("=" * 68)


def note(msg):
    print(f"[..] {msg}")


def ok(msg):
    print(f"[OK] {msg}")


def warn(msg):
    print(f"[!!] {msg}")


def fail(msg):
    print(f"[XX] {msg}")


def die(msg, code=1):
    fail(msg)
    sys.exit(code)


def need_file(path, what="文件"):
    p = Path(path)
    if not p.is_absolute():
        p = (ROOT / p)
    if not p.exists():
        die(f"{what}不存在: {p}")
    return p


def need_exe(path, what="可执行文件"):
    p = Path(path)
    if not p.exists():
        die(f"{what}缺失: {p}")
    return p


def stem_of(path):
    return Path(path).stem


def ensure_dirs():
    for d in (DIR_STEMS, DIR_OUT, DIR_SUB, DIR_TMP):
        d.mkdir(parents=True, exist_ok=True)


def run(cmd, env=None, quiet=False):
    if not quiet:
        print(f"$ {subprocess.list2cmdline([str(c) for c in cmd])}")
    t0 = time.time()
    rc = subprocess.call([str(c) for c in cmd], env=env or build_env(), cwd=str(ROOT))
    dt = time.time() - t0
    if rc != 0:
        fail(f"命令失败 (exit {rc})，耗时 {dt:.1f}s")
    return rc, dt


def capture(cmd, env=None, timeout=180):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout,
                       env=env or build_env(), cwd=str(ROOT))
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def media_info(path):
    """用 ffprobe 读时长 / 标签 / 内嵌封面。"""
    code, out, err = capture([FFPROBE, "-v", "error", "-print_format", "json",
                              "-show_format", "-show_streams", path])
    if code != 0:
        return {"duration": None, "tags": {}, "has_cover": False, "raw": err}
    try:
        data = json.loads(out)
    except Exception:
        return {"duration": None, "tags": {}, "has_cover": False, "raw": out[:300]}
    fmt = data.get("format", {}) or {}
    tags = {str(k).lower(): v for k, v in (fmt.get("tags", {}) or {}).items()}
    dur = fmt.get("duration")
    has_cover = any(
        s.get("codec_type") == "video" and (s.get("disposition", {}) or {}).get("attached_pic") == 1
        for s in (data.get("streams", []) or [])
    )
    return {"duration": float(dur) if dur else None, "tags": tags,
            "has_cover": has_cover, "raw": ""}


def fmt_ts(sec):
    sec = max(0.0, float(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def human(nbytes):
    x = float(nbytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or unit == "TB":
            return f"{x:.1f}{unit}" if unit != "B" else f"{int(x)}B"
        x /= 1024


def dwidth(s):
    """终端显示宽度：CJK 算 2 列。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def pad(s, width):
    return s + " " * max(0, width - dwidth(s))


# ---------------------------------------------------------------- doctor
def py_probe(py, code, timeout=180):
    try:
        rc, out, err = capture([str(py), "-c", code], timeout=timeout)
        return rc == 0, (out or err)[-300:]
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def cmd_doctor(args):
    hr("环境自检")
    results = []

    def add(critical, label, passed, detail=""):
        results.append((critical, label, bool(passed), detail))
        mark = "OK" if passed else ("XX" if critical else "!!")
        print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))

    # 1 工作区与磁盘
    du = shutil.disk_usage(str(ROOT))
    add(True, "工作区", ROOT.exists(), str(ROOT))
    free_gb = du.free / 1024 ** 3
    add(False, "磁盘剩余", free_gb > 3, f"{free_gb:.1f}GB 可用（分离 1 首歌约需 0.3-1GB）")

    # 2 两套解释器
    add(True, "主环境 python310", PY_MAIN.exists(), str(PY_MAIN) if PY_MAIN.exists() else "缺失")
    add(True, "高级环境 .venv-as", PY_AS.exists(), str(PY_AS) if PY_AS.exists() else "缺失")

    if PY_MAIN.exists():
        rc, out, _ = capture([str(PY_MAIN), "-c", "import sys;print(sys.version.split()[0])"], timeout=60)
        add(True, "主环境版本", rc == 0, out)
        rc, out, _ = capture([str(PY_MAIN), "-c",
                              "import importlib.metadata as m;print(m.version('spleeter'))"], timeout=180)
        add(True, "spleeter 可导入", rc == 0, out if rc == 0 else "导入失败，见下方诊断")

    # 3 ffmpeg / ffprobe
    for exe, label in ((FFMPEG, "ffmpeg"), (FFPROBE, "ffprobe")):
        if exe.exists():
            rc, out, err = capture([str(exe), "-version"], timeout=60)
            ver = (out.splitlines() or [""])[0]
            add(True, label, rc == 0 and "version" in ver, ver[:80])
        else:
            add(True, label, False, f"缺失 {exe}")

    # 4 模型
    for name in ("2stems", "4stems", "5stems"):
        d = MODELS / name
        has = d.exists() and any(f.name.startswith("model") for f in d.iterdir()) if d.exists() else False
        probe = (d / ".probe").exists() if d.exists() else False
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) if d.exists() else 0
        add(name == "2stems", f"spleeter 模型 {name}", has,
            f"{human(size)}" + ("" if probe else " (无 .probe，首次使用会重新校验)"))

    # 5 UVR 模型
    if UVR_MODELS.exists():
        files = [f for f in UVR_MODELS.iterdir() if f.is_file() and f.suffix in {".ckpt", ".th", ".yaml", ".onnx"}]
        add(False, "UVR 模型缓存", bool(files),
            f"{len(files)} 个 / {human(sum(f.stat().st_size for f in files))} @ {UVR_MODELS}")
        for f in sorted(files):
            print(f"        · {f.name}  {human(f.stat().st_size)}")
    else:
        add(False, "UVR 模型缓存", False, f"目录不存在: {UVR_MODELS}（uvr 子命令会创建）")

    # 6 GPU（重，--quick 跳过）
    if not args.quick and PY_MAIN.exists():
        note("检查 TensorFlow GPU（约 10-20 秒）…")
        code = ("import os;os.environ['TF_CPP_MIN_LOG_LEVEL']='3';"
                "import tensorflow as tf;"
                "g=tf.config.list_physical_devices('GPU');print(len(g), [x.name for x in g])")
        passed, detail = py_probe(PY_MAIN, code, timeout=300)
        add(False, "TF GPU 可用", passed and detail.startswith(("1", "2")), detail)

    if not args.quick and PY_AS.exists():
        note("检查 torch/CUDA（约 10-20 秒）…")
        code = ("import torch;print('cuda', torch.cuda.is_available(), torch.__version__)"
                ";print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu only')")
        passed, detail = py_probe(PY_AS, code, timeout=300)
        add(False, "torch CUDA 可用", passed, detail.replace("\n", " | "))

        code = ("import audio_separator, librosa, soundfile;"
                "import importlib.metadata as m;"
                "print(m.version('audio-separator'), librosa.__version__)")
        passed, detail = py_probe(PY_AS, code, timeout=300)
        add(False, "audio-separator / librosa", passed, detail)

    # 7 目录可写
    ensure_dirs()
    for d in (DIR_STEMS, DIR_OUT, DIR_SUB, DIR_TMP):
        probe = d / "._wtest"
        try:
            probe.write_text("x", encoding="utf-8")
            probe.unlink()
            add(False, f"可写 {d.name}", True, str(d))
        except Exception as e:
            add(True, f"可写 {d.name}", False, f"{type(e).__name__}: {e}")

    # 汇总
    hr("结果")
    crit = [r for r in results if r[0] and not r[2]]
    soft = [r for r in results if not r[0] and not r[2]]
    print(f"检查 {len(results)} 项：关键失败 {len(crit)}，警告 {len(soft)}")
    if crit:
        for _, label, _, detail in crit:
            print(f"  [XX] {label}: {detail}")
        print("\n关键项失败时命令无法运行。常见修复：")
        print("  · 解释器/工具缺失 → 检查 tools\\python310、tools\\ffmpeg、tools\\cuda 是否被移动")
        print("  · spleeter 导入失败 → tools\\python310\\python.exe -m pip install -r tools\\requirements-main.txt")
        print("  · 依赖损坏 → 重新执行 music freeze 对照版本")
        return 1
    if soft:
        print("\n警告项不影响主流程（GPU 不可用会自动回落 CPU，速度约慢 10-20 倍）。")
    ok("环境就绪")
    return 0


# ---------------------------------------------------------------- separate
def cmd_separate(args):
    files = [need_file(f, "音频") for f in args.files]
    need_exe(PY_MAIN, "主环境解释器")
    parts = args.parts
    if not re.fullmatch(r"[245]stems", parts):
        die("--parts 只能是 2stems / 4stems / 5stems")
    if not (MODELS / parts).exists():
        die(f"模型目录不存在: {MODELS / parts}\n      首次使用请先 'music doctor' 查看，或手动放入 pretrained_models\\{parts}")

    ensure_dirs()
    single = len(files) == 1
    if args.out:
        outdir = Path(args.out)
        if not outdir.is_absolute():
            outdir = ROOT / outdir
    else:
        outdir = DIR_STEMS / f"{stem_of(files[0])}_{parts}" if single else DIR_STEMS / f"batch_{parts}"
    outdir.mkdir(parents=True, exist_ok=True)

    hr(f"spleeter 分离 · {parts}")
    print(f"输入 {len(files)} 个文件 → {outdir}")

    codec = args.codec
    if args.nested or not single:
        fmt = "{filename}/{instrument}.{codec}"
    else:
        fmt = "{instrument}.{codec}"

    cmd = [str(PY_MAIN), "-m", "spleeter", "separate"]
    cmd += [str(f) for f in files]
    cmd += ["-o", str(outdir), "-p", f"spleeter:{parts}", "-f", fmt]
    if args.duration:
        cmd += ["-d", str(args.duration)]
    if codec == "mp3":
        cmd += ["-c", "mp3", "-b", args.bitrate]
    if args.verbose:
        cmd += ["--verbose"]

    note("提醒：分离任务请串行跑，并行会因 8GB 显存不足 OOM")
    rc, dt = run(cmd)

    # 汇总产物
    print()
    produced = sorted([p for p in outdir.rglob(f"*.{codec}")], key=lambda p: p.name)
    if produced:
        ok(f"完成，{len(produced)} 个文件，耗时 {dt:.0f}s（{dt / max(1.0, sum((media_info(f)['duration'] or 0) for f in files)):.1f}x 实时）")
        for p in produced:
            print(f"  {p.name:24s} {human(p.stat().st_size):>9s}  {p}")
    else:
        fail("没有产物，请检查上方日志")
        return 1
    return 0


# ---------------------------------------------------------------- uvr
def cmd_uvr(args):
    src = need_file(args.file, "音频")
    need_exe(AUDIO_SEP, "audio-separator")
    model = UVR_SHORTCUTS.get(args.model.lower(), args.model)
    ensure_dirs()
    UVR_MODELS.mkdir(parents=True, exist_ok=True)
    outdir = Path(args.out) if args.out else (DIR_STEMS / f"{stem_of(src)}_uvr_{Path(model).stem[:20]}")
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    if not (UVR_MODELS / model).exists() and not model.endswith(".yaml"):
        warn(f"本地没有 {model}，将以官方地址下载（GitHub 可能截断）")

    hr(f"audio-separator · {Path(model).name}")
    cmd = [str(AUDIO_SEP), str(src), "-m", model,
           "--output_dir", str(outdir),
           "--output_format", args.format,
           "--model_file_dir", str(UVR_MODELS)]
    if args.single_stem:
        cmd += ["--single_stem", args.single_stem]
    if args.pitch_shift:
        cmd += ["--mdxc_pitch_shift", str(args.pitch_shift)]
    rc, dt = run(cmd)

    produced = sorted(outdir.glob(f"*.{args.format.lower()}"))
    print()
    if produced:
        ok(f"完成，{len(produced)} 个文件，耗时 {dt:.0f}s")
        for p in produced:
            print(f"  {p.name}  {human(p.stat().st_size)}")
        if len(produced) == 2:
            print("\n小技巧：要独立和声轨，用 karaoke 模型 + bs 模型各跑一次，"
                  "然后 和声 = karaoke 伴奏 - bs 伴奏（见 tools\\分离\\make_backup_vocals.py）")
    else:
        fail("没有产物，请检查上方日志")
        return 1
    return 0


# ---------------------------------------------------------------- lyrics
def _lrclib(params, timeout=30):
    url = "https://lrclib.net/api/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "music.py/1.0 (local)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def lrc_to_srt(lrc):
    entries = []
    for line in lrc.splitlines():
        times = re.findall(r"\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]", line)
        text = re.sub(r"\[.*?\]", "", line).strip()
        if not times or not text:
            continue
        for m, s in times:
            entries.append((int(m) * 60 + float(s), text))
    entries.sort()
    # 去掉紧邻重复行（同一句反复出现）
    dedup = []
    for t, text in entries:
        if dedup and dedup[-1][1] == text and t - dedup[-1][0] < 1.0:
            continue
        dedup.append((t, text))
    out = []
    for i, (t, text) in enumerate(dedup):
        end = dedup[i + 1][0] if i + 1 < len(dedup) else t + 4.0
        if end - t < 0.3:
            end = t + 0.3
        ms, rem = divmod(int(round(t * 1000)), 1000)
        h, rem2 = divmod(ms, 3600)
        mi, se = divmod(rem2, 60)
        ms2, rem3 = divmod(int(round(end * 1000)), 1000)
        h2, rem4 = divmod(ms2, 3600)
        mi2, se2 = divmod(rem4, 60)
        out.append(f"{i + 1}\n{h:02d}:{mi:02d}:{se:02d},{rem:03d} --> "
                   f"{h2:02d}:{mi2:02d}:{se2:02d},{rem3:03d}\n{text}\n")
    return out


# ---------------------------------------------------------------- ASR 兼底
def _has_asr():
    script = SCRIPT_SUB / "asr_lrc.py"
    if not script.exists() or not PY_AS.exists():
        return False
    rc, _, _ = capture([str(PY_AS), "-c", "import faster_whisper"], timeout=90)
    return rc == 0


def _asr_lyrics(src, prefix=None, model="small"):
    script = SCRIPT_SUB / "asr_lrc.py"
    if not script.exists():
        die(f"ASR 脚本缺失: {script}")
    need_exe(PY_AS, "高级环境解释器")
    stem = prefix or src.stem
    DIR_SUB.mkdir(parents=True, exist_ok=True)
    srt = DIR_SUB / f"{stem}_ASR歌词.srt"
    lrc = DIR_SUB / f"{stem}_ASR歌词.lrc"
    env = build_env()
    env["HF_ENDPOINT"] = env.get("HF_ENDPOINT") or "https://hf-mirror.com"
    hr(f"离线识别歌词（faster-whisper {model}）· {stem}")
    note("提示：唱段识别只作草稿，需要人工修改后当字幕用")
    rc, dt = run([str(PY_AS), str(script), str(src), "--srt", str(srt),
                  "--lrc", str(lrc), "--model", model], env=env)
    if rc == 0:
        ok(f"完成，耗时 {dt:.0f}s -> {srt.relative_to(ROOT)}")
    return rc


def cmd_lyrics(args):
    src = need_file(args.file, "音频") if args.file else None
    if getattr(args, "asr", False):
        if not src:
            die("--asr 需要指定音频文件")
        return _asr_lyrics(src, args.prefix, args.asr_model)
    info = media_info(src) if src else {"duration": None, "tags": {}}
    tags = info.get("tags", {})
    junk = {"kuwo", "kugou", "qq", "netease", "unknown", "audio", "untitled",
            "未知", "未知艺术家", "various artists", "网易云音乐", "qq音乐", "酷我音乐"}

    def _clean(v):
        return (v or "").strip()

    def _bad(v):
        return (not v) or v.lower() in junk

    artist = _clean(args.artist)
    title = _clean(args.title)

    # 文件名 "歌手 - 歌名" 最可靠；否则退回音频标签
    if src and not (artist and title):
        name = src.stem
        if " - " in name:
            fa, ft = [x.strip() for x in name.split(" - ", 1)]
            if not artist and not _bad(fa):
                artist = fa
            if not title and not _bad(ft):
                title = ft
    if not artist:
        a = _clean(tags.get("artist") or tags.get("album_artist"))
        if not _bad(a) and a.lower() != (title or "").lower():
            artist = a
    if not title:
        t = _clean(tags.get("title"))
        if not _bad(t) and t.lower() != (artist or "").lower():
            title = t
    if not title and src:
        title = src.stem
    if not title:
        die("无法确定歌名，请用 --title / --artist 指定")

    hr(f"lrclib 歌词 · {artist} - {title}" if artist else f"lrclib 歌词 · {title}")

    params = {"track_name": title}
    if artist:
        params["artist_name"] = artist

    def _search(p):
        recs = []
        last = None
        for attempt in range(4):
            try:
                recs = _lrclib(p) or []
                last = None
                break
            except Exception as e:
                last = e
                warn(f"请求失败({type(e).__name__}) 第 {attempt + 1}/4 次，重试…")
                time.sleep(1.5 * (attempt + 1))
        return recs, last

    recs, last_err = _search(params)
    if not recs and last_err is None and artist:
        recs, last_err = _search({"q": f"{artist} {title}".strip()})
    if not recs and last_err is None:
        recs, last_err = _search({"q": title})
    if not recs:
        if src and _has_asr():
            warn("lrclib 没结果，改用离线识别（faster-whisper）")
            return _asr_lyrics(src, args.prefix, args.asr_model)
        if last_err is not None:
            die(f"lrclib 不可达（{type(last_err).__name__}: {last_err}）\n"
                f"      lrclib 偏发 503，稍后重试；或手动写 字幕\\{title}_歌词.srt")
        die(f"lrclib 查无此歌（关键词: {title} / {artist or '-'}）\n"
            f"      可换关键词: music lyrics <file> --title \"...\" --artist \"...\"\n"
            f"      或直接用离线识别: music lyrics <file> --asr")

    target = info.get("duration") or 0
    cands = [r for r in recs if r.get("syncedLyrics")]
    if not cands:
        die(f"找到 {len(recs)} 条记录但都没有同步歌词（仅纯文本），无法直接出字幕。\n"
            f"      可换关键词再试，或手动制作 SRT。")

    if target:
        cands.sort(key=lambda r: abs((r.get("duration") or 0) - target))
    best = cands[0]
    delta = abs((best.get("duration") or 0) - target) if target else 0
    print(f"选中: {best.get('artistName')} - {best.get('trackName')} | {best.get('albumName')} "
          f"| 时长 {best.get('duration')}s (差 {delta:.1f}s)")
    if target and delta > 5:
        warn("版本时长差超过 5 秒，时间轴可能整体偏移；可用 --title 换一条记录")
    if len(cands) > 1:
        print("其他候选：")
        for r in cands[1:4]:
            print(f"  · {r.get('artistName')} - {r.get('trackName')} | {r.get('albumName')} | {r.get('duration')}s")

    lrc = best["syncedLyrics"]
    srt_items = lrc_to_srt(lrc)
    if not srt_items:
        die("歌词解析为空")

    DIR_SUB.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or (src.stem if src else f"{artist}_{title}")
    lrc_path = DIR_SUB / f"{prefix}_歌词.lrc"
    srt_path = DIR_SUB / f"{prefix}_歌词.srt"
    lrc_path.write_text(lrc, encoding="utf-8")
    srt_path.write_text("\n".join(srt_items), encoding="utf-8-sig")
    print()
    ok(f"写出 {len(srt_items)} 条字幕")
    print(f"  {lrc_path}")
    print(f"  {srt_path}")
    first_sync = next((ln for ln in srt_items[0].splitlines() if "-->" in ln), "")
    if first_sync:
        print(f"  首句开始 {first_sync.split('-->')[0].strip().replace(',', '.')}")
    print(f"  下一步: music ass \"{srt_path}\"")
    return 0


# ---------------------------------------------------------------- ass
def cmd_ass(args):
    srt = need_file(args.srt, "SRT")
    script = SCRIPT_SUB / ("srt2ass_light.py" if args.light else "srt2ass.py")
    if not script.exists():
        die(f"样式脚本缺失: {script}")
    out = Path(args.out) if args.out else (DIR_SUB / (srt.stem + ".ass"))
    if not out.is_absolute():
        out = ROOT / out
    ensure_dirs()
    run([PY_MAIN, script, str(srt), str(out)])
    if out.exists():
        ok(f"{out}  ({human(out.stat().st_size)})")
        return 0
    fail("未生成 ass")
    return 1


# ---------------------------------------------------------------- render
def extract_cover(audio, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    rc, out, err = capture([FFMPEG, "-y", "-i", str(audio), "-map", "0:v:0",
                            "-c", "copy", "-frames:v", "1", str(dest)], timeout=120)
    return dest.exists() and dest.stat().st_size > 0


def cmd_render(args):
    audio = need_file(args.audio, "音频")
    need_exe(FFMPEG, "ffmpeg")
    info = media_info(audio)
    dur = info.get("duration")
    if args.duration:
        dur = min(dur or args.duration, float(args.duration))

    # 1 字幕
    ass_path = None
    if args.ass:
        ass_path = need_file(args.ass, "ASS")
    elif args.srt:
        srt = need_file(args.srt, "SRT")
        script = SCRIPT_SUB / ("srt2ass_light.py" if args.light else "srt2ass.py")
        ass_path = DIR_TMP / (srt.stem + ".ass")
        DIR_TMP.mkdir(parents=True, exist_ok=True)
        if not args.no_subs:
            run([PY_MAIN, script, str(srt), str(ass_path)], quiet=True)
            if not ass_path.exists():
                die(f"字幕转换失败: {ass_path}")
    if args.no_subs:
        ass_path = None

    # 2 封面
    cover = Path(args.cover) if args.cover else None
    if cover and not cover.is_absolute():
        cover = ROOT / cover
    if cover and not cover.exists():
        die(f"封面不存在: {cover}")
    if not cover:
        if info.get("has_cover"):
            cover = DIR_TMP / f"{stem_of(audio)}_cover.jpg"
            if extract_cover(audio, cover):
                ok(f"从音频提取内嵌封面: {cover.name}")
            else:
                cover = None
        if not cover:
            die("没有封面。请用 --cover 指定图片，"
                "或先用 tools\\图片\\make_bg.py 生成渐变背景。")

    # 3 filter 脚本
    W, H, FG = args.width, args.height, args.fg
    esc = ass_path.as_posix().replace(":", "\\:", 1) if ass_path else ""
    chain = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
             f"crop={W}:{H},boxblur={args.blur}[bgb];"
             f"[0:v]scale={FG}:{FG}[fg];"
             f"[bgb][fg]overlay=(W-w)/2:(H-h)/2")
    if ass_path:
        chain += f",subtitles='{esc}'"
    chain += "[v]"
    DIR_TMP.mkdir(parents=True, exist_ok=True)
    fscript = DIR_TMP / f"{stem_of(audio)}_filter.txt"
    fscript.write_text(chain, encoding="utf-8")

    out = Path(args.out) if args.out else (DIR_OUT / f"{stem_of(audio)}_歌词视频.mp4")
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    hr("渲染视频")
    print(f"封面 {cover.name} | 时长 {dur:.1f}s | {W}x{H} @ {args.fps}fps | 字幕 {'有' if ass_path else '无'}")
    cmd = [str(FFMPEG), "-y",
           "-loop", "1", "-i", str(cover),
           "-i", str(audio),
           "-filter_complex_script", str(fscript),
           "-map", "[v]", "-map", "1:a",
           "-c:v", "h264_nvenc", "-preset", args.preset, "-cq", str(args.crf),
           "-r", str(args.fps), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", args.abitrate,
           "-movflags", "+faststart", "-shortest",
           "-loglevel", "error", "-stats_period", "60"]
    if args.duration:
        cmd += ["-t", str(float(args.duration))]
    cmd += [str(out)]
    rc, dt = run(cmd)
    if out.exists() and out.stat().st_size > 0:
        ok(f"完成 {out.name}  {human(out.stat().st_size)}  耗时 {dt:.0f}s")
        print(f"  {out}")
        return 0
    fail(f"渲染失败，检查 filter: {fscript}")
    return 1


# ---------------------------------------------------------------- analyze
def cmd_analyze(args):
    src = need_file(args.file, "音频")
    script = SCRIPT_ANA / "vocal_profile.py"
    if not script.exists():
        die(f"分析脚本缺失: {script}")
    need_exe(PY_AS, "高级环境解释器")

    wav = src
    if src.suffix.lower() != ".wav":
        DIR_TMP.mkdir(parents=True, exist_ok=True)
        wav = DIR_TMP / (src.stem + "_analyze.wav")
        note(f"转码为 wav（librosa 无法直读 {src.suffix}）…")
        rc, _ = run([FFMPEG, "-y", "-i", str(src), "-ac", "1", "-ar", "44100",
                     "-loglevel", "error", str(wav)], quiet=True)
        if not wav.exists():
            die("转码失败")

    label = args.label or src.stem
    hr(f"演唱分析 · {label}")
    rc, dt = run([PY_AS, str(script), str(wav), label])
    ok(f"耗时 {dt:.0f}s")
    return rc


# ---------------------------------------------------------------- report
def cmd_report(args):
    src = need_file(args.file, "音频")
    script = SCRIPT_ANA / "pitch_report.py"
    if not script.exists():
        die(f"脚本缺失: {script}")
    need_exe(PY_AS, "高级环境解释器")

    wav = src
    if src.suffix.lower() not in {".wav", ".flac"}:
        DIR_TMP.mkdir(parents=True, exist_ok=True)
        wav = DIR_TMP / (src.stem + "_pitch.wav")
        note(f"转码为 wav…")
        run([FFMPEG, "-y", "-i", str(src), "-ac", "1", "-ar", "44100",
             "-loglevel", "error", str(wav)], quiet=True)
        if not wav.exists():
            die("转码失败")

    label = args.label or src.stem
    png = Path(args.png) if args.png else ROOT / "档案" / "报告" / f"{label}_音准.png"
    jout = Path(args.json) if args.json else ROOT / "档案" / "报告" / f"{label}_音准.json"
    png.parent.mkdir(parents=True, exist_ok=True)
    hr(f"音准可视化报告 · {label}")
    cmd = [str(PY_AS), str(script), str(wav), "--label", label,
           "--png", str(png), "--json", str(jout)]
    rc, dt = run(cmd)
    if rc == 0:
        ok(f"完成，耗时 {dt:.0f}s -> {png.relative_to(ROOT)}")
    return rc

# ---------------------------------------------------------------- freeze
WHEEL_RE = re.compile(r"^(.+?)-(\d[^-]*)-(?:cp|py)\d", re.I)


def _sanitize_freeze(text, extra_index=None, seen_index=False):
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if "@ file:///" in ln:
            name = ln.split(" @ ")[0].strip()
            wheel = urllib.parse.unquote(ln.split("file:///")[-1].split("#")[0])
            base = Path(wheel).name
            m = WHEEL_RE.match(base)
            ver = m.group(2) if m else ""
            out.append(f"# [local wheel] {name}{('==' + ver) if ver else ''}  <- {base}")
            if name.lower() == "torch" and extra_index and not seen_index:
                out.append(f"--extra-index-url {extra_index}")
                seen_index = True
            if ver:
                out.append(f"{name}=={ver}")
            continue
        out.append(ln)
    return out


def cmd_freeze(args):
    hr("导出依赖锁定")
    targets = [
        ("main", PY_MAIN, TOOLS / "requirements-main.txt",
         "# main env: tools/python310 (Python 3.10.11) | spleeter 2.4 + tensorflow-gpu 2.9.3",
         None),
        ("as", PY_AS, TOOLS / "requirements-as.txt",
         "# advanced env: .venv-as (Python 3.10.11) | torch cu126 + audio-separator",
         "https://mirrors.aliyun.com/pytorch-wheels/cu126"),
    ]
    for label, py, dest, header, idx in targets:
        if not Path(py).exists():
            warn(f"{label}: 解释器缺失 {py}，跳过")
            continue
        rc, out, err = capture([str(py), "-m", "pip", "freeze"], timeout=300)
        if rc != 0:
            fail(f"{label}: pip freeze 失败 {err[:200]}")
            continue
        lines = _sanitize_freeze(out, extra_index=idx)
        stamp = time.strftime("%Y-%m-%d %H:%M")
        body = [header, f"# generated {stamp} by 'music freeze'",
                f"# install: \"{py}\" -m pip install -r \"{dest}\" --no-cache-dir", ""]
        dest.write_text("\n".join(body + lines) + "\n", encoding="utf-8")
        ok(f"{dest.name}  {len(lines)} 行  {human(dest.stat().st_size)}")
    return 0


# ---------------------------------------------------------------- info
def cmd_info(args):
    hr(f"music.py {VERSION}")
    rows = [
        ("工作区", ROOT),
        ("主环境 python", PY_MAIN),
        ("高级环境 python", PY_AS),
        ("audio-separator", AUDIO_SEP),
        ("ffmpeg", FFMPEG),
        ("ffprobe", FFPROBE),
        ("CUDA 运行时", CUDA_BIN),
        ("spleeter 模型", MODELS),
        ("UVR 模型缓存", UVR_MODELS),
        ("分轨输出", DIR_STEMS),
        ("成品输出", DIR_OUT),
        ("字幕", DIR_SUB),
        ("素材/中间文件", DIR_TMP),
    ]
    for label, p in rows:
        mark = "OK" if Path(p).exists() else "--"
        print(f"  [{mark}] {pad(label, 22)}{p}")
    du = shutil.disk_usage(str(ROOT))
    print(f"  磁盘 {du.used / 1024 ** 3:.1f}GB 已用 / {du.free / 1024 ** 3:.1f}GB 可用")
    print("\n子命令: doctor separate uvr lyrics ass render analyze freeze info")
    print("帮助:   music <子命令> -h")
    return 0


# ---------------------------------------------------------------- pack
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a"}


def _flac_one(src, dst, level=8):
    if dst.exists():
        dst.unlink()
    rc, out, err = capture([str(FFMPEG), "-y", "-i", str(src), "-map_metadata", "0",
                            "-c:a", "flac", "-compression_level", str(level),
                            "-loglevel", "error", str(dst)], timeout=3600)
    if rc != 0 or not dst.exists() or dst.stat().st_size == 0:
        if dst.exists():
            dst.unlink()
        return False, (err or out).strip()[-300:]
    return True, ""


def cmd_pack(args):
    roots = [Path(d).resolve() for d in (args.dirs or [DIR_STEMS])]
    for r in roots:
        if not r.exists():
            die(f"目录不存在: {r}")
    files = []
    for r in roots:
        files += [f for f in r.rglob("*.wav") if f.stat().st_size >= args.min_mb * 1024 * 1024]
    files.sort(key=lambda f: -f.stat().st_size)
    hr(f"wav -> flac · {'执行' if args.apply else '预览（--apply 才真转）'}")
    if not files:
        warn(f"没有大于 {args.min_mb}MB 的 wav")
        return 0
    total = sum(f.stat().st_size for f in files)
    print(f"待处理 {len(files)} 个文件，合计 {human(total)}（预估可省约 {human(total * 0.52)}）")
    print()
    done, freed, failed = 0, 0, 0
    for i, src in enumerate(files, 1):
        dst = src.with_suffix(".flac")
        tag = pad(f"[{i}/{len(files)}]", 9)
        if not args.apply:
            print(f"{tag}{pad(str(src), 74)}{human(src.stat().st_size)}")
            continue
        okc, msg = _flac_one(src, dst, args.level)
        if not okc:
            failed += 1
            fail(f"{tag}{src.name}  转换失败 {msg}")
            continue
        before = src.stat().st_size
        after = dst.stat().st_size
        st = src.stat()
        os.utime(str(dst), (st.st_atime, st.st_mtime))
        if not args.keep:
            src.unlink()
        done += 1
        freed += before - after
        print(f"{tag}{pad(src.name, 52)}{human(before):>9} -> {human(after):>9}  省 {100 * (1 - after / before):.0f}%")
    print()
    if not args.apply:
        print("确认无误后执行：music pack --apply")
        return 0
    ok(f"转换 {done} 个，失败 {failed} 个，释放 {human(freed)}")
    return 1 if failed else 0


# ---------------------------------------------------------------- meta
def _find_source(base):
    best = None
    for ext in (".flac", ".wav", ".mp3", ".m4a"):
        for c in (ROOT / "素材").rglob(f"*{ext}"):
            if base in c.stem:
                if best is None or len(c.stem) < len(best.stem):
                    best = c
    return best


def _project_meta(pdir, source):
    stems = []
    for f in sorted(pdir.rglob("*")):
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
            stems.append({
                "file": f.relative_to(pdir).as_posix(),
                "format": f.suffix.lower().lstrip("."),
                "bytes": f.stat().st_size,
                "duration": round(media_info(f).get("duration") or 0, 2),
            })
    base = pdir.name.split("_")[0]
    lyrics = sorted(p.name for p in DIR_SUB.glob(f"*{base}*")) if DIR_SUB.exists() else []
    videos = sorted(p.name for p in DIR_OUT.glob(f"*{base}*")) if DIR_OUT.exists() else []
    info = {
        "project": pdir.name,
        "source": str(source.relative_to(ROOT)) if source else None,
        "source_duration": round(media_info(source).get("duration") or 0, 2) if source else None,
        "stems": stems,
        "total_bytes": sum(s["bytes"] for s in stems),
        "lyrics": lyrics,
        "videos": videos,
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return info


def cmd_meta(args):
    if args.projects:
        dirs = [DIR_STEMS / p if not Path(p).is_absolute() else Path(p) for p in args.projects]
    else:
        dirs = sorted(p for p in DIR_STEMS.iterdir() if p.is_dir()) if DIR_STEMS.exists() else []
    hr(f"项目元数据 · {len(dirs)} 个项目")
    index = []
    for pdir in dirs:
        if not pdir.exists():
            warn(f"跳过不存在的项目: {pdir}")
            continue
        src = _find_source(pdir.name.split("_")[0])
        info = _project_meta(pdir, src)
        (pdir / "项目.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append({k: info[k] for k in ("project", "source", "source_duration",
                                          "total_bytes", "lyrics", "videos", "updated")})
        index[-1]["stems"] = len(info["stems"])
        print(f"  {pad(pdir.name, 34)}{len(info['stems']):>3} 个分轨  {human(info['total_bytes']):>9}"
              f"  字幕 {len(info['lyrics'])}  视频 {len(info['videos'])}")
    out = ROOT / "档案" / "项目索引.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                               "projects": index}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print()
    ok(f"索引 -> {out.relative_to(ROOT)}（{len(index)} 项）")
    return 0


# ---------------------------------------------------------------- sidr
def cmd_sidr(args):
    mix = need_file(args.mix, "混音")
    voc = need_file(args.vocals, "人声")
    acc = need_file(args.accomp, "伴奏")
    hr("分离质量自评（SI-SDR）")
    cmd = [str(PY_AS), str(TOOLS / "分析" / "sidr.py"), str(mix), str(voc), str(acc)]
    if args.ref_vocals:
        cmd += ["--ref-vocals", str(need_file(args.ref_vocals, "参考人声"))]
    if args.ref_accomp:
        cmd += ["--ref-accomp", str(need_file(args.ref_accomp, "参考伴奏"))]
    if args.json:
        cmd += ["--json", str(args.json)]
    rc, dt = run(cmd)
    if rc == 0:
        ok(f"完成，耗时 {dt:.1f}s")
    return rc


# ---------------------------------------------------------------- chords
def cmd_chords(args):
    src = need_file(args.audio, "音频")
    stem = src.stem
    srt = Path(args.srt) if args.srt else DIR_SUB / f"{stem}_和弦.srt"
    jout = Path(args.json) if args.json else ROOT / "档案" / "报告" / f"{stem}_chords.json"
    srt.parent.mkdir(parents=True, exist_ok=True)
    jout.parent.mkdir(parents=True, exist_ok=True)
    hr(f"和弦识别 · {stem}")
    cmd = [str(PY_AS), str(TOOLS / "分析" / "chords.py"), str(src),
           "--srt", str(srt), "--json", str(jout), "--min-dur", str(args.min_dur)]
    if args.bpm:
        cmd += ["--bpm", str(args.bpm)]
    if args.capo:
        cmd += ["--capo", str(args.capo)]
    if args.no_viterbi:
        cmd += ["--no-viterbi"]
    rc, dt = run(cmd)
    if rc == 0:
        ok(f"完成，耗时 {dt:.1f}s -> {srt.relative_to(ROOT)}")
    return rc

# ---------------------------------------------------------------- batch
def _iter_audio(paths):
    exts = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in exts:
                    yield f
        elif p.is_file():
            yield p


def cmd_batch(args):
    files = list(_iter_audio(args.inputs))
    if not files:
        die("没找到音频文件")
    hr(f"批量流水线 · {len(files)} 个文件")
    me = [str(PY_MAIN), str(Path(__file__).resolve())]
    done, failed = [], []
    for i, f in enumerate(files, 1):
        note(f"[{i}/{len(files)}] {f.name}")
        out = Path(args.out) / f.stem if args.out else DIR_STEMS / f"{f.stem}_{args.parts}"
        cmd = me + ["separate", str(f), "--parts", args.parts, "-o", str(out)]
        if args.duration:
            cmd += ["-d", str(args.duration)]
        rc, _ = run(cmd, quiet=True)
        if rc != 0:
            failed.append(f.name)
            warn(f"分离失败：{f.name}")
            continue
        if args.lyrics:
            run(me + ["lyrics", str(f)], quiet=True)
        if args.chords:
            run(me + ["chords", str(f)], quiet=True)
        done.append(f.name)
    print()
    ok(f"完成 {len(done)}/{len(files)}")
    for n in failed:
        print(f"  [XX] {n}")
    return 0 if done else 1


# ---------------------------------------------------------------- publish
def cmd_publish(args):
    src = need_file(args.file, "音频")
    title = args.title or src.stem
    dest = ROOT / "发布包" / title
    dest.mkdir(parents=True, exist_ok=True)
    hr(f"投稿包 · {title}")

    media = need_file(args.video, "视频") if args.video else src
    target = dest / media.name
    if media.resolve() != target.resolve():
        shutil.copy2(media, target)
    note(f"媒体  {media.name}  {human(target.stat().st_size)}")

    # 封面：16:9 1146x717
    img_dir = ROOT / "素材" / "图片"
    cover_src = Path(args.cover) if args.cover else None
    if not cover_src:
        # 1) 同名图片 2) 图片名是音频名的一部分（如 吉他手.webp ← 陈绮贞 - 吉他手.flac）
        for ext in (".webp", ".jpg", ".jpeg", ".png"):
            cand = img_dir / f"{src.stem}{ext}"
            if cand.exists():
                cover_src = cand
                break
        if not cover_src and img_dir.exists():
            imgs = [p for p in img_dir.iterdir()
                    if p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}
                    and p.stem in src.stem and len(p.stem) >= 2]
            if imgs:
                cover_src = max(imgs, key=lambda p: len(p.stem))
    cover_dst = dest / "封面.jpg"
    if cover_src and cover_src.exists():
        rc, _ = run([FFMPEG, "-y", "-i", str(cover_src),
                     "-vf", "scale=1146:717:force_original_aspect_ratio=increase,crop=1146:717",
                     "-q:v", "2", "-loglevel", "error", str(cover_dst)], quiet=True)
        if cover_dst.exists():
            note(f"封面  封面.jpg  {human(cover_dst.stat().st_size)}")
    else:
        warn("没找到封面（用 --cover 指定，或放到 素材\\图片\\<歌名>.webp）")

    # 字幕：歌词 / 和弦
    for srt in sorted(DIR_SUB.glob(f"*{src.stem}*.srt")):
        shutil.copy2(srt, dest / srt.name)
        note(f"字幕  {srt.name}")

    tags = args.tags or "翻唱,吉他,弹唱,伴奏"
    info = [
        f"标题：{title}",
        "",
        "分区：音乐 → 翻唱 / 演奏",
        f"标签：{tags}",
        "",
        "简介：",
        f"{args.blurb or '自弹自唱 / 伴奏字幕版，欢迎提意见。'}",
        "",
        "分轨/字幕由本地 Spleeter + BS-Roformer 制作（仅用于学习与练习）。",
    ]
    chords = DIR_SUB / f"{src.stem}_和弦.srt"
    if chords.exists():
        info += ["", f"和弦时间轴见附件 {chords.name}（自动识别，仅供参考）。"]
    (dest / "投稿信息.txt").write_text("\n".join(info), encoding="utf-8-sig")
    note("文案  投稿信息.txt")

    print()
    ok(f"发布包已就绪 → {dest.relative_to(ROOT)}")
    print("  上传时：标题/简介/标签直接复制 投稿信息.txt；封面用 封面.jpg；字幕可上传后挂字幕轨")
    return 0


# ---------------------------------------------------------------- log / trend
TRAIN_LOG = ROOT / "档案" / "训练记录.jsonl"
SPARK = "▁▂▃▄▅▆▇█"


def _read_log():
    if not TRAIN_LOG.exists():
        return []
    out = []
    for ln in TRAIN_LOG.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def cmd_log(args):
    from datetime import date, datetime
    src = need_file(args.file, "音频")
    label = args.label or src.stem
    jout = ROOT / "档案" / "报告" / f"{label}_音准.json"
    hr(f"记录演唱训练 · {label}")
    rc, _ = run([str(PY_MAIN), str(Path(__file__).resolve()), "report", str(src),
                 "--label", label, "--json", str(jout)], quiet=True)
    if rc != 0 or not jout.exists():
        die("音准分析失败，先单独跑 music report 看报错")
    try:
        st = json.loads(jout.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"报告解析失败：{e}")

    rec = {
        "date": date.today().isoformat(),
        "time": datetime.now().strftime("%H:%M"),
        "label": label,
        "song": args.song or "",
        "note": args.note or "",
        "notes": st.get("notes"),
        "median_abs_cents": st.get("median_abs_cents"),
        "mean_abs_cents": st.get("mean_abs_cents"),
        "pct_25": st.get("pct_25"),
        "long_cents": (st.get("long_notes") or {}).get("median_cents"),
        "short_cents": (st.get("short_notes") or {}).get("median_cents"),
        "range": f"{st.get('range_low')}-{st.get('range_high')}",
        "zones": st.get("zones"),
    }
    TRAIN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(TRAIN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    ok(f"已记录 → {TRAIN_LOG.relative_to(ROOT)}")
    print(f"  音准中位 {rec['median_abs_cents']} 音分 · ±25内 {rec['pct_25']}% · "
          f"长音 {rec['long_cents']} · 音域 {rec['range']}")
    recs = _read_log()
    if len(recs) >= 2:
        prev = recs[-2]
        if prev.get("median_abs_cents") is not None and rec["median_abs_cents"] is not None:
            d = rec["median_abs_cents"] - prev["median_abs_cents"]
            tag = "进步" if d < -1 else ("变差" if d > 1 else "持平")
            print(f"  对比上次（{prev['date']} {prev['label']}）：{d:+.1f} 音分 → {tag}")
    return 0


def cmd_trend(args):
    recs = _read_log()
    if not recs:
        die("还没有训练记录，先跑：music log <录音文件> --song 歌名")
    if args.label:
        recs = [r for r in recs if args.label in (r.get("label") or "")]
    recs = recs[-args.last:]
    if not recs:
        die("没有匹配的记录")
    hr(f"演唱训练趋势 · {len(recs)} 次")
    print(f"  {'日期':<11}{'标签':<14}{'音准中位':>9}{'长音':>7}{'短音':>7}{'±25%':>7}  音域")
    print("  " + "-" * 78)
    for r in recs:
        print(f"  {r['date']:<11}{(r['label'] or '')[:12]:<14}"
              f"{r['median_abs_cents']:>9}{str(r['long_cents']):>7}{str(r['short_cents']):>7}"
              f"{r['pct_25']:>7}  {r['range']}")

    vals = [r["median_abs_cents"] for r in recs if r.get("median_abs_cents") is not None]
    if vals:
        lo, hi = min(vals), max(vals)
        span = max(1e-6, hi - lo)
        line = "".join(SPARK[min(7, int((hi - v) / span * 7.99))] for v in vals)
        print(f"\n  走势（块越高=音分越小=越准）\n  {line}   {vals[0]} → {vals[-1]}")
        first, last = vals[0], vals[-1]
        print(f"  累计变化 {last - first:+.1f} 音分（{len(vals)} 次记录）")

    md = ROOT / "档案" / "训练趋势.md"
    lines = ["# 演唱训练趋势", "", "| 日期 | 标签 | 音准中位(音分) | 长音 | 短音 | ±25% | 音域 | 备注 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in recs:
        lines.append(f"| {r['date']} | {r['label']} | {r['median_abs_cents']} | {r['long_cents']} | "
                     f"{r['short_cents']} | {r['pct_25']} | {r['range']} | {r.get('note') or ''} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  已导出 {md.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------- gui
def cmd_gui(args):
    script = TOOLS / "gui.py"
    if not script.exists():
        die(f"GUI 脚本缺失: {script}")
    hr("本地 Web GUI")
    print(f"  打开 http://127.0.0.1:{args.port}")
    rc, _ = run([str(PY_MAIN), str(script), "--port", str(args.port)])
    return rc
# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="music",
        description="D:\\musicProduct 统一入口 —— 分离 / 歌词 / 字幕 / 视频 / 声学分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  music doctor\n"
               "  music separate \"素材\\歌.flac\" -p 5stems\n"
               "  music uvr \"素材\\歌.flac\" -m karaoke\n"
               "  music lyrics \"素材\\歌.flac\"\n"
               "  music render \"素材\\歌.flac\" --srt \"字幕\\歌_歌词.srt\" --cover \"素材\\图片\\封面.jpg\"\n"
               "  music analyze \"素材\\录音.m4a\"\n")
    ap.add_argument("-V", "--version", action="version", version=f"music.py {VERSION}")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("doctor", help="环境自检")
    p.add_argument("--quick", action="store_true", help="跳过 GPU 检查（更快）")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("separate", help="spleeter 分离（GPU）")
    p.add_argument("files", nargs="+", help="音频文件，可多个")
    p.add_argument("-p", "--parts", default="2stems", help="2stems/4stems/5stems（默认 2stems）")
    p.add_argument("-o", "--out", help="输出目录（默认 分轨\\<歌名>_<模型>）")
    p.add_argument("-d", "--duration", type=float, help="只处理前 N 秒（试听/测试）")
    p.add_argument("-c", "--codec", default="wav", choices=["wav", "mp3"], help="输出格式")
    p.add_argument("-b", "--bitrate", default="192k", help="mp3 码率（默认 192k）")
    p.add_argument("--nested", action="store_true", help="按子目录存放（旧版布局）")
    p.add_argument("--verbose", action="store_true", help="输出详细日志")
    p.set_defaults(func=cmd_separate)

    p = sub.add_parser("uvr", help="audio-separator 高质量分离")
    p.add_argument("file", help="音频文件")
    p.add_argument("-m", "--model", default="bs",
                   help="bs(人声最干净) / karaoke(留和声) / demucs6(6轨) 或完整模型文件名")
    p.add_argument("-o", "--out", help="输出目录")
    p.add_argument("--format", default="WAV", help="输出格式（默认 WAV，可 MP3/FLAC）")
    p.add_argument("--single-stem", dest="single_stem", help="只输出单轨，如 Instrumental")
    p.add_argument("--pitch-shift", dest="pitch_shift", type=int, help="MDXC 变调半音数")
    p.set_defaults(func=cmd_uvr)

    p = sub.add_parser("lyrics", help="lrclib 抓歌词 -> lrc + srt")
    p.add_argument("file", nargs="?", help="音频文件（用于读标签/时长）")
    p.add_argument("--title", help="歌名")
    p.add_argument("--artist", help="歌手")
    p.add_argument("--prefix", help="输出文件名前缀")
    p.add_argument("--asr", action="store_true", help="不查 lrclib，直接用 faster-whisper 识别")
    p.add_argument("--asr-model", dest="asr_model", default="small",
                   help="识别模型 tiny/base/small/medium（默认 small）")
    p.set_defaults(func=cmd_lyrics)

    p = sub.add_parser("ass", help="srt -> ass")
    p.add_argument("srt", help="SRT 文件")
    p.add_argument("-o", "--out", help="输出路径")
    p.add_argument("--light", action="store_true", help="浅色底样式（深字奶油描边）")
    p.set_defaults(func=cmd_ass)

    p = sub.add_parser("render", help="封面+歌词 -> mp4")
    p.add_argument("audio", help="音频文件")
    p.add_argument("--srt", help="歌词 SRT（自动转 ASS）")
    p.add_argument("--ass", help="已转好的 ASS")
    p.add_argument("--cover", help="封面图片（缺省尝试音频内嵌封面）")
    p.add_argument("-o", "--out", help="输出 mp4（默认 成品\\<歌名>_歌词视频.mp4）")
    p.add_argument("--light", action="store_true", help="字幕用浅色底样式")
    p.add_argument("--no-subs", dest="no_subs", action="store_true", help="不加字幕")
    p.add_argument("--fps", type=int, default=15, help="帧率（静态图 15 足够，默认 15）")
    p.add_argument("--crf", type=int, default=22, help="CQ 质量（默认 22，越小越清晰）")
    p.add_argument("--preset", default="p7", help="nvenc 预设（默认 p7）")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fg", type=int, default=700, help="封面尺寸（默认 700）")
    p.add_argument("--blur", default="25:5", help="背景模糊（默认 25:5）")
    p.add_argument("--abitrate", default="320k", help="音频码率（默认 320k）")
    p.add_argument("--duration", type=float, help="只渲染前 N 秒（测试用）")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("analyze", help="演唱声学分析")
    p.add_argument("file", help="录音文件（任意格式，自动转 wav）")
    p.add_argument("--label", help="报告标题")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("report", help="音准可视化报告（PNG + json）")
    p.add_argument("file", help="录音/分轨文件")
    p.add_argument("--label", help="报告标题（默认文件名）")
    p.add_argument("--png", help="输出 PNG 路径")
    p.add_argument("--json", help="输出 json 路径")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("freeze", help="重新生成两套 requirements.txt")
    p.set_defaults(func=cmd_freeze)

    p = sub.add_parser("info", help="显示路径配置")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("pack", help="分轨 wav -> flac 压缩（省约一半体积）")
    p.add_argument("dirs", nargs="*", help="要处理的目录（默认 分轨\\）")
    p.add_argument("--apply", action="store_true", help="真正执行（默认只预览）")
    p.add_argument("--keep", action="store_true", help="保留原 wav")
    p.add_argument("--min-mb", dest="min_mb", type=float, default=2.0, help="只处理大于 N MB 的文件（默认 2）")
    p.add_argument("--level", type=int, default=8, help="flac 压缩等级 0-12（默认 8）")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("meta", help="生成项目元数据 项目.json + 全局索引")
    p.add_argument("projects", nargs="*", help="项目目录名（默认 分轨\\ 下全部）")
    p.set_defaults(func=cmd_meta)

    p = sub.add_parser("sidr", help="分离质量自评（SI-SDR / 串音 / 电平）")
    p.add_argument("mix", help="原始混音")
    p.add_argument("vocals", help="分离出的人声")
    p.add_argument("accomp", help="分离出的伴奏")
    p.add_argument("--ref-vocals", dest="ref_vocals", help="参考人声（可选，算真 SI-SDR）")
    p.add_argument("--ref-accomp", dest="ref_accomp", help="参考伴奏（可选）")
    p.add_argument("--json", help="结果写入 json")
    p.set_defaults(func=cmd_sidr)

    p = sub.add_parser("chords", help="和弦识别（Viterbi 平滑 + 转位）-> SRT")
    p.add_argument("audio")
    p.add_argument("--srt", help="输出 SRT（默认 字幕\\<歌名>_和弦.srt）")
    p.add_argument("--json", help="输出 json（默认 档案\\报告\\<歌名>_chords.json）")
    p.add_argument("--bpm", type=float, help="固定 BPM（节拍跟踪不稳时用）")
    p.add_argument("--capo", type=int, default=0, help="变调夹品位（显示手位和弦）")
    p.add_argument("--no-viterbi", dest="no_viterbi", action="store_true", help="不做平滑")
    p.add_argument("--min-dur", dest="min_dur", type=float, default=0.35, help="最短和弦时长")
    p.set_defaults(func=cmd_chords)

    p = sub.add_parser("batch", help="批量：目录内全部音频连续分离（可选歌词/和弦）")
    p.add_argument("inputs", nargs="+", help="音频文件或目录")
    p.add_argument("--parts", default="2stems", choices=["2stems", "4stems", "5stems"])
    p.add_argument("-d", "--duration", type=float, help="只处理前 N 秒")
    p.add_argument("--lyrics", action="store_true", help="顺带抓歌词")
    p.add_argument("--chords", action="store_true", help="顺带识别和弦")
    p.add_argument("--out", help="输出根目录（默认 分轨\\<歌名>_<模型>）")
    p.set_defaults(func=cmd_batch)

    p = sub.add_parser("publish", help="生成 B站投稿包（媒体+封面+字幕+文案）")
    p.add_argument("file", help="音频（用于命名/找封面字幕）")
    p.add_argument("--video", help="成品视频（缺省用音频本身）")
    p.add_argument("--cover", help="自定义封面图")
    p.add_argument("--title", help="视频标题（默认文件名）")
    p.add_argument("--tags", help="标签，逗号分隔")
    p.add_argument("--blurb", help="简介正文")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("log", help="记录一次练习（音准指标入档）")
    p.add_argument("file")
    p.add_argument("--label", help="标签（默认文件名）")
    p.add_argument("--song", help="歌曲名")
    p.add_argument("--note", help="备注")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("trend", help="训练趋势（表格 + 走势图 + Markdown）")
    p.add_argument("--label", help="只看标签包含该词的记录")
    p.add_argument("--last", type=int, default=20, help="最近 N 条（默认 20）")
    p.set_defaults(func=cmd_trend)

    p = sub.add_parser("gui", help="本地 Web GUI（浏览器里点按钮）")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_gui)

    args = ap.parse_args(argv)
    if not getattr(args, "cmd", None):
        ap.print_help()
        return 0
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
