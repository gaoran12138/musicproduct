# -*- coding: utf-8 -*-
"""Counting Stars 歌词: 生成 1x / 1.2x / 1.4x 三份 SRT+LRC (时间轴按倍速压缩)"""
import urllib.request, json, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

# 1) 搜索 lrclib
s = json.loads(fetch("https://lrclib.net/api/search?track_name=Counting%20Stars&artist_name=OneRepublic"))
best = None
for r in s:
    if r.get("syncedLyrics"):
        dur = r.get("duration") or 0
        if best is None or abs(dur - 257) < abs((best.get("duration") or 0) - 257):
            best = r
print("picked:", best.get("trackName"), "|", best.get("artistName"), "| dur", best.get("duration"))
lrc = best["syncedLyrics"]

# 2) 解析 LRC 条目
entries = []  # (sec, text)
for line in lrc.splitlines():
    times = re.findall(r"\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]", line)
    text = re.sub(r"\[.*?\]", "", line).strip()
    if not times:
        continue
    for m, s2 in times:
        sec = int(m) * 60 + float(s2)
        entries.append((sec, text))
entries.sort()
print("lyric lines:", len(entries))

# 3) 按倍速生成
def fmt_srt(sec):
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def fmt_lrc(sec):
    m = int(sec // 60)
    s = sec - m * 60
    return f"[{m:02d}:{s:05.2f}]"

for speed in (1.0, 1.2, 1.4):
    scaled = [(t / speed, text) for t, text in entries]
    # SRT
    srt = []
    for i, (t, text) in enumerate(scaled):
        end = scaled[i + 1][0] if i + 1 < len(scaled) else t + 4.0
        srt.append(f"{i+1}\n{fmt_srt(t)} --> {fmt_srt(end)}\n{text}\n")
    fn_srt = rf"D:\musicProduct\字幕\Counting_Stars_歌词_{speed:g}x.srt"
    with open(fn_srt, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(srt))
    # LRC
    fn_lrc = rf"D:\musicProduct\字幕\Counting_Stars_歌词_{speed:g}x.lrc"
    with open(fn_lrc, "w", encoding="utf-8") as f:
        f.write(f"[ti:Counting Stars]\n[ar:OneRepublic]\n")
        for t, text in scaled:
            f.write(f"{fmt_lrc(t)}{text}\n")
    print(f"{speed:g}x -> {len(srt)} 条 SRT, 时长 {fmt_srt(scaled[-1][0])}")

# 预览 1x 前几条
print("\n--- 1x 预览 ---")
print(open(r"D:\musicProduct\字幕\Counting_Stars_歌词_1x.srt", encoding="utf-8-sig").read()[:300])
