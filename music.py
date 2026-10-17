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


def cmd_lyrics(args):
    src = need_file(args.file, "音频") if args.file else None
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
        if last_err is not None:
            die(f"lrclib 不可达（{type(last_err).__name__}: {last_err}）\n"
                f"      lrclib 偏发 503，稍后重试；或手动写 字幕\\{title}_歌词.srt")
        die(f"lrclib 查无此歌（关键词: {title} / {artist or '-'}）\n"
            f"      可换关键词: music lyrics <file> --title \"...\" --artist \"...\"")

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

    p = sub.add_parser("freeze", help="重新生成两套 requirements.txt")
    p.set_defaults(func=cmd_freeze)

    p = sub.add_parser("info", help="显示路径配置")
    p.set_defaults(func=cmd_info)

    args = ap.parse_args(argv)
    if not getattr(args, "cmd", None):
        ap.print_help()
        return 0
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
