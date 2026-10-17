# -*- coding: utf-8 -*-
"""Counting Stars: 1.2x + 1.5x + 0.8x 三段首尾拼接成一份中英双语 SRT"""
import re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TRANS = {
    "Counting Stars - OneRepublic": "数星星 - 共和乐队",
    "Lately, I've been, I've been losing sleep": "最近我一直辗转难眠",
    "Dreaming about the things that we could be": "幻想着我们可能成为的模样",
    "But baby, I've been, I've been praying hard": "宝贝，我一直虔诚祈祷",
    'Said, "No more counting dollars, we\'ll be counting stars"': "告诉自己，别再数钞票，我们去数星星",
    "Yeah, we'll be counting stars": "是啊，我们要去数星星",
    "I see this life, like a swinging vine": "我把这人生看作摇摆的藤蔓",
    "Swing my heart across the line": "让我的心越过界限摆动",
    "And in my face is flashing signs": "我脸上闪烁着信号",
    "Seek it out and ye shall find": "用心探寻，你就会找到",
    "Old, but I'm not that old": "老了，但我还没那么老",
    "Young, but I'm not that bold": "年轻，但也没那么大胆",
    "And I don't think the world is sold": "我不相信这个世界",
    "On just doing what we're told": "只会听从别人的摆布",
    "I feel something so right, doing the wrong thing": "做着错事，我却感觉如此正确",
    "And I feel something so wrong, doing the right thing": "做着对的事，我却感觉如此错误",
    "I couldn't lie, couldn't lie, couldn't lie": "我无法再欺骗、欺骗、欺骗",
    "Everything that kills me makes me feel alive": "置我于死地的一切，让我感觉活着",
    "I feel your love, and I feel it burn": "我感受着你的爱，感受它在燃烧",
    "Down this river, every turn": "顺流而下，每一个转弯",
    "Hope is our four-letter word": "希望是我们唯一的信条",
    "Make that money, watch it burn": "赚来的钱，看着它燃烧",
    "Everything that drowns me makes me wanna fly": "令我沉溺的一切，让我想要飞翔",
    "Oh, take that money, watch it burn": "拿走那些钱，看着它燃烧",
    "Sink in the river the lessons I've learned": "把学到的教训沉入河中",
    "Yeah": "耶",
}

entries = []
with open(r"D:\musicProduct\字幕\Counting_Stars_歌词_1x_中英.srt", encoding="utf-8-sig") as f:
    content = f.read()
for b in re.split(r"\r?\n\r?\n", content.strip()):
    lines = b.splitlines()
    if len(lines) < 2:
        continue
    m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1])
    t0 = int(m[1])*3600+int(m[2])*60+int(m[3])+int(m[4])/1000
    t1 = int(m[5])*3600+int(m[6])*60+int(m[7])+int(m[8])/1000
    text = "\n".join(lines[2:]).strip()
    entries.append((t0, t1, text))
# 只保留英文行(第一行)用于重排; 歌词原文
raw = [(t0, t1, text.split("\n")[0]) for t0, t1, text in entries]
song_len = raw[-1][0] + 4.0
print("歌词行:", len(raw), "| 歌曲时长(1x):", round(song_len, 2), "s")

def fmt(sec):
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# 三段: (倍速, 起始偏移)
parts = [(1.2, 0.0), (1.5, 0.0), (0.8, 0.0)]
offset = 0.0
srt = []
idx = 1
for speed, _ in parts:
    seg = sorted((t / speed, text) for t, _, text in raw)
    # 段落开头标签
    srt.append(f"{idx}\n{fmt(offset)} --> {fmt(offset + 1.5)}\n{'' if speed == 1.2 else ''}{speed:g}x")
    idx += 1
    off_start = offset + 1.5
    for i, (t, text) in enumerate(seg):
        end = seg[i + 1][0] if i + 1 < len(seg) else song_len / speed
        cn = TRANS.get(text, "")
        body = text if not cn else f"{text}\n{cn}"
        srt.append(f"{idx}\n{fmt(off_start + t)} --> {fmt(off_start + end)}\n{body}")
        idx += 1
    offset = off_start + song_len / speed

out = r"D:\musicProduct\字幕\Counting_Stars_歌词_拼接_1.2-1.5-0.8_中英.srt"
with open(out, "w", encoding="utf-8-sig") as f:
    f.write("\n".join(srt))
print("总条数:", idx - 1, "| 总时长:", fmt(offset))
print("written:", out)
print("\n--- 预览: 段落边界 ---")
for line in srt:
    if " --> " in line and ("x\n" in line + "\n" or True):
        pass
# 打印标签条目附近
for i, line in enumerate(srt):
    if line.strip() in ("1.2x", "1.5x", "0.8x"):
        print(srt[i-1], "|", line, "| 下一段:", srt[i+3] if i+3 < len(srt) else "")
