# -*- coding: utf-8 -*-
"""把三行字幕拆成 歌词 和 和弦+右手 两个独立 SRT"""
import re, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def parse(path):
    out = []
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    for b in re.split(r"\r?\n\r?\n", content.strip()):
        lines = b.splitlines()
        if len(lines) < 2:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1])
        t0 = int(m[1])*3600+int(m[2])*60+int(m[3])+int(m[4])/1000
        t1 = int(m[5])*3600+int(m[6])*60+int(m[7])+int(m[8])/1000
        out.append((t0, t1, "\n".join(lines[2:]).strip()))
    return out

def fmt(t):
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write(path, es):
    out = []
    for i, (t0, t1, text) in enumerate(es, start=1):
        out.append(f"{i}\n{fmt(t0)} --> {fmt(t1)}\n{text}\n")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(out))

entries = parse(r"D:\musicProduct\字幕\晴天_歌词+和弦+右手.srt")
lyrics_only, top = [], []
for t0, t1, text in entries:
    lines = text.split("\n")
    if len(lines) >= 3 and lines[0].startswith("|"):
        top.append((t0, t1, lines[0] + "\n" + lines[1]))   # 和弦 + 右手
        lyrics_only.append((t0, t1, lines[2]))             # 歌词
    elif len(lines) == 2 and lines[0].startswith("|"):
        top.append((t0, t1, lines[0] + "\n" + lines[1]))
    elif len(lines) == 1 and lines[0].startswith("|"):
        top.append((t0, t1, lines[0]))
    elif len(lines) >= 2 and not lines[0].startswith("|"):
        lyrics_only.append((t0, t1, text))
    else:
        lyrics_only.append((t0, t1, text))

write(r"D:\musicProduct\字幕\晴天子幕A_歌词.srt", lyrics_only)
write(r"D:\musicProduct\字幕\晴天子幕B_和弦右手.srt", top)
print("歌词条数:", len(lyrics_only), "| 和弦+右手条数:", len(top))
