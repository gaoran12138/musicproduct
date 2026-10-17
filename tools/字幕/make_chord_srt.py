# -*- coding: utf-8 -*-
"""《晴天》词+和弦 SRT：按小节排版，和弦行 + 歌词行，逐句不遗漏。"""
import re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def parse_srt(path):
    entries = []  # (index, t0, t1, text)
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    for b in re.split(r"\r?\n\r?\n", content.strip()):
        lines = b.splitlines()
        if len(lines) < 2:
            continue
        idx = int(lines[0])
        m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1])
        if not m:
            continue
        t0 = int(m[1])*3600 + int(m[2])*60 + int(m[3]) + int(m[4])/1000
        t1 = int(m[5])*3600 + int(m[6])*60 + int(m[7]) + int(m[8])/1000
        entries.append((idx, t0, t1, "\n".join(lines[2:]).strip()))
    return entries

def fmt(t):
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

lyrics = parse_srt(r"D:\musicProduct\字幕\晴天_歌词.srt")
print("lyric entries:", len(lyrics), "| line numbers:", [e[0] for e in lyrics])

# ---- 和弦分配（按原 SRT 行号） ----
VERSE = ["Em7", "Cadd9", "G", "D/F#"]              # 主歌每行 1 小节 1 和弦
CHORUS_PAIR = {                                      # 副歌每行 2 小节
    14: ["G", "Em"], 15: ["C", "D"], 16: ["B7", "Em"], 17: ["C", "D"],
    18: ["G", "Em"], 19: ["C", "D"], 20: ["B7", "Em"], 21: ["C", "D"],
    28: ["G", "Em"], 29: ["C", "D"], 30: ["B7", "Em"], 31: ["C", "D"],
    32: ["G", "Em"], 33: ["C", "D"], 34: ["B7", "Em"], 35: ["C", "D"],
    36: ["G", "Em"], 37: ["C", "D"], 38: ["B7", "Em"], 39: ["C", "D"],
    40: ["G", "Em"], 41: ["C", "D"], 42: ["B7", "Em"], 43: ["C", "D"],
}
TRANSITION = ["Em7", "C", "D"]                       # 过渡行 3 小节

chord_by_line = {}
for i in range(1, 13):                               # 主歌1: 行1-12
    chord_by_line[i] = [VERSE[(i - 1) % 4]]
chord_by_line[13] = TRANSITION
for i in range(23, 27):                              # 主歌2: 行23-26
    chord_by_line[i] = [VERSE[(i - 23) % 4]]
chord_by_line[27] = TRANSITION
for k, v in CHORUS_PAIR.items():
    chord_by_line[k] = v

def chord_line(chords):
    return "| " + " | ".join(chords) + " |"

# ---- 纯器乐段落（每小节一条） ----
def bars(start, end, chords):
    n = len(chords)
    step = (end - start) / n
    return [(start + i * step, start + (i + 1) * step, chord_line([c])) for i, c in enumerate(chords)]

instrumental = []
instrumental += bars(0.0, 4.0, ["G调  4/4拍  ♩=68"])            # 开头信息
instrumental += bars(4.0, 29.36, VERSE * 2)                      # 前奏 8 小节
instrumental += bars(142.41, 154.63, ["Em7", "C", "G", "D"] * 2) # 间奏 8 小节
instrumental += bars(265.60, 269.75, ["G"])                      # 结尾

# ---- 歌词行: 和弦行(按小节) + 歌词行 ----
lyric_entries = []
missing = []
for idx, t0, t1, text in lyrics:
    ch = chord_by_line.get(idx)
    if ch is None:
        missing.append(idx)
        lyric_entries.append((t0, t1, text))
    else:
        lyric_entries.append((t0, t1, chord_line(ch) + "\n" + text))

assert not missing, f"缺失和弦的行号: {missing}"
print("all lyric lines have chords ✓")

all_entries = instrumental + lyric_entries
all_entries.sort(key=lambda x: x[0])

def write_srt(path, entries):
    out = []
    for i, (t0, t1, text) in enumerate(entries, start=1):
        out.append(f"{i}\n{fmt(t0)} --> {fmt(t1)}\n{text}\n")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(out))

write_srt(r"D:\musicProduct\字幕\晴天_歌词+和弦.srt", all_entries)
write_srt(r"D:\musicProduct\字幕\晴天_和弦.srt", [(t0, t1, text.split("\n")[0]) for t0, t1, text in all_entries])

print("total entries:", len(all_entries))
print("--- 预览: 前奏 + 主歌1 + 副歌 ---")
for t0, t1, text in all_entries:
    if t0 < 4.0 or 28 < t0 < 60 or 84 < t0 < 130:
        print(fmt(t0), "->", fmt(t1), "|", text.replace("\n", " / "))
