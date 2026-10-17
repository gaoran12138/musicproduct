# -*- coding: utf-8 -*-
"""为浅底画面生成深字浅边的 ASS 字幕 (印刷感)"""
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

entries = parse_srt(sys.argv[1])
ass_path = sys.argv[2]

# 样式: 深暖褐字 + 奶油色描边 (浅底上印刷感; 深色块上依然可辨)
header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,38,&H002A2320,&H000000FF,&H00D5E8F2,&H64000000,0,0,0,0,100,100,1,0,1,3,1.5,2,60,60,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
events = [f"Dialogue: 0,{ts(t0)},{ts(t1)},Default,,0,0,0,,{text.replace(chr(10), chr(92)+'N')}"
          for t0, t1, text in entries]
with open(ass_path, "w", encoding="utf-8-sig") as f:
    f.write(header + "\n".join(events) + "\n")
print("ASS:", len(events), "->", ass_path)
