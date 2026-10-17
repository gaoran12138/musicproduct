# -*- coding: utf-8 -*-
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import guitarpro

song = guitarpro.parse(r"D:\musicProduct\吉他谱\晴天.gp4")
gt = song.tracks[1]
bt = song.tracks[4]
headers = song.measureHeaders
NOTE = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def m_notes(m):
    midis = []
    for v in m.voices:
        for b in v.beats:
            for n in b.notes:
                if n.realValue is not None:
                    midis.append(n.realValue)
    return midis

# 小节时长分布
durs = {}
for h in headers:
    d = h.length
    durs[d] = durs.get(d, 0) + 1
print("小节长度分布(ticks):", durs)

# 前 16 小节 与 副歌区 40-52 小节: 时间/音符/和弦候选
for mi in list(range(0, 16)) + list(range(40, 54)):
    if mi >= len(gt.measures):
        continue
    midis = m_notes(gt.measures[mi])
    bmidis = m_notes(bt.measures[mi]) if mi < len(bt.measures) else []
    start = headers[mi].start
    length = headers[mi].length
    pcs = sorted(set(m % 12 for m in midis))
    bpcs = sorted(set(m % 12 for m in bmidis))
    notes_str = ",".join(NOTE[p] for p in pcs)
    bass = min(bmidis) % 12 if bmidis else (min(midis) % 12 if midis else None)
    print(f"m{mi}: start={start} len={length} 吉他1音级=[{notes_str}] bass={NOTE[bass] if bass is not None else '?'} 贝司音级={[NOTE[p] for p in bpcs]}")
