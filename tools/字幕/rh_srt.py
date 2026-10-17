# -*- coding: utf-8 -*-
"""GP4 -> 词+和弦+右手 三行字幕 (直接计算, 不依赖中间文件)"""
import sys, re
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import guitarpro

GP_PATH = r"D:\musicProduct\吉他谱\晴天.gp4"
AUDIO_DUR = 269.75
NOTE = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
TEMPLATES = [
    ("", {0,4,7}), ("m", {0,3,7}), ("7", {0,4,7,10}), ("maj7", {0,4,7,11}),
    ("m7", {0,3,7,10}), ("sus4", {0,5,7}), ("sus2", {0,2,7}), ("add9", {0,2,4,7}),
    ("6", {0,4,7,9}), ("m6", {0,3,7,9}), ("dim", {0,3,6}), ("aug", {0,4,8}),
    ("9", {0,2,4,7,10}), ("m9", {0,2,3,7,10}), ("7sus4", {0,5,7,10}), ("m7b5", {0,3,6,10}),
    ("5", {0,7}),
]

def guess_chord(pcs, bass_pc):
    if not pcs:
        return None
    pcs = set(pcs)
    best = None
    for root in range(12):
        ivset = set((pc - root) % 12 for pc in pcs)
        for q, tpl in TEMPLATES:
            covered = tpl & ivset
            score = len(covered) * 10 - (len(ivset) - len(covered)) * 3
            if covered == tpl:
                score += 20
            if len(tpl) >= 3 and len(covered) == len(tpl) - 1:
                score -= 2
            if root == bass_pc:
                score += 6
            if best is None or score > best[0]:
                best = (score, root, q)
    if best is None:
        return None
    _, root, q = best
    name = NOTE[root] + q
    if q == "5" and len(pcs) >= 3:
        name = NOTE[root]
    if bass_pc != root and q != "5":
        name += "/" + NOTE[bass_pc]
    return name

song = guitarpro.parse(GP_PATH)
gt = song.tracks[1]
bt = song.tracks[4]
aux = [song.tracks[2], song.tracks[3]]
headers = song.measureHeaders
scale = AUDIO_DUR / (headers[-1].start + headers[-1].length)

def m_notes(m):
    pcs, midis = [], []
    for v in m.voices:
        for b in v.beats:
            for n in b.notes:
                if n.realValue is not None:
                    midis.append(n.realValue)
                    pcs.append(n.realValue % 12)
    return pcs, midis

def rh_of_measure(m):
    beats = []
    for v in m.voices:
        for b in v.beats:
            if not b.notes:
                continue
            pos = b.startInMeasure if b.startInMeasure is not None else b.start % 3840
            beats.append((int(round(pos / 240)), len(b.notes), sorted(n.string for n in b.notes)[0]))
    beats.sort()
    if not beats:
        return ("", "rest")
    if all(n <= 2 for _, n, _ in beats):
        seq = [s for _, _, s in beats]
        return (f"分解琶音 {'-'.join(str(x) for x in seq[:4])}", "arp")
    played = set((p16 // 4, (p16 % 4) // 2) for p16, _, _ in beats)
    per = []
    for b in range(4):
        on, off = (b, 0) in played, (b, 1) in played
        per.append("↓↑" if on and off else "↓" if on else "↑" if off else "·")
    return (" ".join(per), "strum")

measures = []
prev = None
for mi, m in enumerate(gt.measures):
    pcs, midis = m_notes(m)
    for a in aux:
        if mi < len(a.measures):
            ap, am = m_notes(a.measures[mi])
            pcs += ap; midis += am
    bp, bm = m_notes(bt.measures[mi]) if mi < len(bt.measures) else ([], [])
    pcs += bp; midis += bm
    ch = guess_chord(pcs, min(midis) % 12) if midis else prev
    prev = ch
    rh, rtype = rh_of_measure(m)
    ws = headers[mi].start * scale
    we = (headers[mi].start + headers[mi].length) * scale
    measures.append((ws, we, ch, rh, rtype, mi + 1))

def fmt(t):
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_lyrics(path):
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
        out.append((int(lines[0]), t0, t1, "\n".join(lines[2:]).strip()))
    return out

lyrics = parse_lyrics(r"D:\musicProduct\字幕\晴天_歌词.srt")

def in_window(t0, t1):
    return [(ch, rh) for ws, we, ch, rh, rt, num in measures if ch and ws < t1 and we > t0]

def dedup(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out

entries = []
entries.append((0.0, 4.0, "| G调  4/4拍  ♩=68 |"))
# 前奏 (无词) 逐小节
for ws, we, ch, rh, rt, num in measures:
    if we <= 29.36 and ch and rh:
        entries.append((ws, we, f"| {ch} |\n{rh}"))
# 歌词行
for idx, t0, t1, text in lyrics:
    pair = in_window(t0, t1)
    if pair:
        chs = "| " + " | ".join(dedup([c for c, _ in pair])) + " |"
        rhs = " / ".join(dedup([r for _, r in pair if r]))
        entries.append((t0, t1, chs + "\n" + rhs + "\n" + text))
    else:
        entries.append((t0, t1, text))
# 剩余无词小节
covered = set()
for idx, t0, t1, text in lyrics:
    for ws, we, ch, rh, rt, num in measures:
        if ws < t1 and we > t0:
            covered.add(num)
for ws, we, ch, rh, rt, num in measures:
    if num not in covered and ws > 29.36 and ch and rh:
        entries.append((ws, we, f"| {ch} |\n{rh}"))

entries.sort(key=lambda x: x[0])

def write_srt(path, es):
    out = []
    for i, (t0, t1, text) in enumerate(es, start=1):
        out.append(f"{i}\n{fmt(t0)} --> {fmt(t1)}\n{text}\n")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(out))

write_srt(r"D:\musicProduct\字幕\晴天_歌词+和弦+右手.srt", entries)
write_srt(r"D:\musicProduct\字幕\晴天_右手标识.srt",
          [(t0, t1, text.split("\n")[1]) for t0, t1, text in entries if len(text.split("\n")) > 1 and text.split("\n")[1] and not text.split("\n")[1].startswith("|")])

print("total:", len(entries))
for t0, t1, text in entries[:24]:
    print(fmt(t0), "->", fmt(t1), "|", text.replace("\n", " ⏎ "))
