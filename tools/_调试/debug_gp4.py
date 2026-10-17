# -*- coding: utf-8 -*-
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import guitarpro

song = guitarpro.parse(r"D:\musicProduct\吉他谱\晴天.gp4")
t = song.tracks[1]  # 吉他1
m0 = t.measures[0]
h = m0.header
print("header attrs:", [a for a in dir(h) if not a.startswith("_")])
print("beat attrs:", [a for a in dir(m0.voices[0].beats[0]) if not a.startswith("_")])
for name in ["tempo", "time_signature", "key_signature", "marker", "number"]:
    print("header.", name, "=", getattr(h, name, "<NA>"))
b = m0.voices[0].beats[0]
for name in ["chord", "duration", "start", "notes", "lyrics", "text"]:
    print("beat.", name, "=", getattr(b, name, "<NA>"))
# 打印前 20 个 beats 的和弦尝试
for mi, m in enumerate(t.measures[:12]):
    for v in m.voices:
        for beat in v.beats:
            ch = getattr(beat, "chord", None)
            print("m", mi, "start", getattr(beat, "start", "?"), "chord", getattr(ch, "name", None) if ch else None, "| notes:", len(getattr(beat, "notes", [])))
