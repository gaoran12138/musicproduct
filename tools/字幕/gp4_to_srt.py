# -*- coding: utf-8 -*-
"""从 晴天.gp4 提取逐小节和弦 -> 生成精确时间轴的 词+和弦 SRT"""
import sys, re
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import guitarpro

GP_PATH = r"D:\musicProduct\吉他谱\晴天.gp4"
AUDIO_DUR = 269.75  # 音频总时长(秒)

song = guitarpro.parse(GP_PATH)
gt = song.tracks[1]   # 吉他1 = 节奏和弦轨
bt = song.tracks[4]   # 贝司 = 根音参考
aux_tracks = [song.tracks[2], song.tracks[3]]  # 吉他2/3 补全和弦音
headers = song.measureHeaders

# ---------- 和弦识别 ----------
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
TEMPLATES = [
    ("",       {0, 4, 7}),
    ("m",      {0, 3, 7}),
    ("7",      {0, 4, 7, 10}),
    ("maj7",   {0, 4, 7, 11}),
    ("m7",     {0, 3, 7, 10}),
    ("sus4",   {0, 5, 7}),
    ("sus2",   {0, 2, 7}),
    ("add9",   {0, 2, 4, 7}),
    ("6",      {0, 4, 7, 9}),
    ("m6",     {0, 3, 7, 9}),
    ("dim",    {0, 3, 6}),
    ("aug",    {0, 4, 8}),
    ("9",      {0, 2, 4, 7, 10}),
    ("m9",     {0, 2, 3, 7, 10}),
    ("7sus4",  {0, 5, 7, 10}),
    ("m7b5",   {0, 3, 6, 10}),
    ("5",      {0, 7}),
]

def guess_chord(pcs, bass_pc):
    """pcs: 音级集合; bass_pc: 最低音音级 -> (显示名, root, quality)"""
    if not pcs:
        return None
    pcs = set(pcs)
    best = None
    for root in range(12):
        ivset = set((pc - root) % 12 for pc in pcs)
        for q, tpl in TEMPLATES:
            covered = tpl & ivset
            score = len(covered) * 10 - (len(ivset) - len(covered)) * 3
            if covered == tpl:          # 完整包含和弦音 -> 大加分
                score += 20
            if len(tpl) >= 3 and len(covered) >= len(tpl) - 1 and len(covered) < len(tpl):
                score -= 2              # 缺一音的和弦稍打折
            if root == bass_pc:
                score += 6
            elif bass_pc in ivset and len(tpl) >= 3:
                score += 1
            if best is None or score > best[0]:
                best = (score, root, q, len(tpl))
    if best is None:
        return None
    _, root, q, _ = best
    name = NOTE_NAMES[root] + q
    # 只剩强力和弦(缺三音)且音符>=3时, 按大三和弦名显示 (如 G5 -> G)
    if q == "5" and len(pcs) >= 3:
        name = NOTE_NAMES[root]
    if bass_pc != root and q not in ("5",):
        name += "/" + NOTE_NAMES[bass_pc]
    return name

# ---------- 逐小节收集音符 ----------
def measure_notes(measure):
    pcs, midis = [], []
    for v in measure.voices:
        for b in v.beats:
            for n in b.notes:
                midi = n.realValue
                if midi is None:
                    continue
                midis.append(midi)
                pcs.append(midi % 12)
    return pcs, midis

chords = []  # (start_ticks, chord_name)
prev = None
for mi, m in enumerate(gt.measures):
    pcs, midis = measure_notes(m)
    # 合并吉他2/3 + 贝司的音符补全和弦音
    for aux in aux_tracks:
        if mi < len(aux.measures):
            apcs, amidis = measure_notes(aux.measures[mi])
            pcs += apcs
            midis += amidis
    bpcs, bmidis = measure_notes(bt.measures[mi]) if mi < len(bt.measures) else ([], [])
    pcs += bpcs
    midis += bmidis
    if not midis:
        chords.append((headers[mi].start, prev))
        continue
    bass = min(midis)
    name = guess_chord(pcs, bass % 12)
    prev = name
    chords.append((headers[mi].start, name))

# ---------- ticks -> 秒 (按音频总时长对齐) ----------
last_end = headers[-1].start + headers[-1].length
scale = AUDIO_DUR / last_end
print(f"总 ticks: {last_end} | scale: {scale:.6f} | GP tempo: {song.tempo}")

def t2s(t):
    return t * scale

# ---------- 生成 SRT ----------
def fmt(t):
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# 歌词 (原 SRT)
def parse_lyrics(path):
    out = []
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    for b in re.split(r"\r?\n\r?\n", content.strip()):
        lines = b.splitlines()
        if len(lines) < 2:
            continue
        idx = int(lines[0])
        m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1])
        t0 = int(m[1])*3600+int(m[2])*60+int(m[3])+int(m[4])/1000
        t1 = int(m[5])*3600+int(m[6])*60+int(m[7])+int(m[8])/1000
        out.append((idx, t0, t1, "\n".join(lines[2:]).strip()))
    return out

lyrics = parse_lyrics(r"D:\musicProduct\字幕\晴天_歌词.srt")

# 小节时间窗 (含开始/结束)
measure_windows = []
for mi, (start_t, name) in enumerate(chords):
    end_t = headers[mi].start + headers[mi].length
    measure_windows.append((t2s(start_t), t2s(end_t), name, mi + 1))

def chords_in_window(t0, t1):
    """返回 [t0,t1] 窗口内覆盖的小节和弦列表 (带小节号)"""
    res = []
    for ws, we, name, num in measure_windows:
        if name and ws < t1 and we > t0:
            res.append((num, name, ws, we))
    return res

def chord_bar_line(items):
    return "| " + " | ".join(n for _, n, _, _ in items) + " |"

# 组装
entries = []
# 信息字幕
entries.append((0.0, 4.0, "| G调  4/4拍  ♩=68 |"))
# 前奏(无词): 逐小节和弦
for ws, we, name, num in measure_windows:
    if we <= 29.36 and name:
        entries.append((ws, we, f"| {name} |"))

# 歌词行
missing = []
for idx, t0, t1, text in lyrics:
    items = chords_in_window(t0, t1)
    if not items:
        missing.append(idx)
        entries.append((t0, t1, text))
    else:
        entries.append((t0, t1, chord_bar_line(items) + "\n" + text))

# 间奏/结尾等无词段: 若歌词窗口未覆盖, 补逐小节
covered = set()
for idx, t0, t1, text in lyrics:
    for num, name, ws, we in chords_in_window(t0, t1):
        covered.add(num)
for ws, we, name, num in measure_windows:
    if name and num not in covered and ws > 29.36:
        entries.append((ws, we, f"| {name} |"))

entries.sort(key=lambda x: x[0])

def write_srt(path, es):
    out = []
    for i, (t0, t1, text) in enumerate(es, start=1):
        out.append(f"{i}\n{fmt(t0)} --> {fmt(t1)}\n{text}\n")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(out))

write_srt(r"D:\musicProduct\字幕\晴天_歌词+和弦.srt", entries)
write_srt(r"D:\musicProduct\字幕\晴天_和弦.srt", [(t0, t1, text.split("\n")[0]) for t0, t1, text in entries])

print("missing chords:", missing if missing else "无 ✓")
print("total entries:", len(entries))
# 预览前 30 条
for t0, t1, text in entries[:30]:
    print(fmt(t0), "->", fmt(t1), "|", text.replace("\n", " / "))
