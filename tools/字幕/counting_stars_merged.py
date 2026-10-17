# -*- coding: utf-8 -*-
"""Counting Stars: 1x/1.2x/1.4x 三组时间轴合并为一份 SRT, 每句带中文翻译"""
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

# 从 1x LRC 读取原始条目
entries = []
with open(r"D:\musicProduct\字幕\Counting_Stars_歌词_1x.lrc", encoding="utf-8") as f:
    for line in f:
        times = re.findall(r"\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]", line)
        text = re.sub(r"\[.*?\]", "", line).strip()
        if not times or not text:
            continue
        sec = int(times[0][0]) * 60 + float(times[0][1])
        entries.append((sec, text))
print("非空歌词行:", len(entries))

def fmt(sec):
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# 三份独立文件: 每份 = 该倍速时间轴 + 中英双语
for speed in (1.0, 1.2, 1.4):
    scaled = sorted((t / speed, text) for t, text in entries)
    srt = []
    for i, (t, text) in enumerate(scaled):
        end = scaled[i + 1][0] if i + 1 < len(scaled) else t + 4.0
        cn = TRANS.get(text, "")
        body = text if not cn else f"{text}\n{cn}"
        srt.append(f"{i+1}\n{fmt(t)} --> {fmt(end)}\n{body}\n")
    out = rf"D:\musicProduct\字幕\Counting_Stars_歌词_{speed:g}x_中英.srt"
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(srt))
    print(f"{speed:g}x -> {len(srt)} 条, 时长 {fmt(scaled[-1][0])}, {out}")
# 预览: 1x 开头 + 1.2x 同一句对比
print("\n--- 预览(1x 开头) ---")
for b in srt[:9]:
    print(b)
