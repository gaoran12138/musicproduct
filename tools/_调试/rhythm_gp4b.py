# -*- coding: utf-8 -*-
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import guitarpro

song = guitarpro.parse(r"D:\musicProduct\吉他谱\晴天.gp4")
gt = song.tracks[1]

def beats_of_measure(m):
    out = []
    for v in m.voices:
        for b in v.beats:
            if not b.notes:
                continue
            strings = sorted(n.string for n in b.notes)
            pos = b.startInMeasure if b.startInMeasure is not None else b.start % 3840
            out.append((int(round(pos / 240)), strings))
    return sorted(out)

for mi in [0, 1, 4, 5, 8, 40, 41]:
    print(f"--- m{mi} ---")
    for pos, strings in beats_of_measure(gt.measures[mi]):
        print(f"  16分位{pos:2d}: 弦 {strings}")
