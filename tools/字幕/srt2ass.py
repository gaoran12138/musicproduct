# -*- coding: utf-8 -*-
"""SRT -> ASS (底部白色描边样式)"""
import re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def parse_srt(path):
    out = []
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    for b in re.split(r"\n\s*\n", content.strip()):
        lines = b.splitlines()
        if len(lines) < 2:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1])
        t0 = int(m[1])*3600+int(m[2])*60+int(m[3])+int(m[4])/1000
        t1 = int(m[5])*3600+int(m[6])*60+int(m[7])+int(m[8])/1000
        out.append((t0, t1, "\n".join(lines[2:]).strip()))
    return out

def ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

srt_path = sys.argv[1] if len(sys.argv) > 1 else r"D:\musicProduct\字幕\Radiohead_WeirdFishes_歌词.srt"
ass_path = sys.argv[2] if len(sys.argv) > 2 else srt_path.rsplit(".", 1)[0] + ".ass"
entries = parse_srt(srt_path)

header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,34,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2.5,1,2,60,60,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

events = []
for t0, t1, text in entries:
    text = text.replace("\n", "\\N")
    events.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},Default,,0,0,0,,{text}")

with open(ass_path, "w", encoding="utf-8-sig") as f:
    f.write(header + "\n".join(events) + "\n")
print("ASS entries:", len(events), "->", ass_path)
