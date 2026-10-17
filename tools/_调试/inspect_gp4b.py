# -*- coding: utf-8 -*-
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import guitarpro

song = guitarpro.parse(r"D:\musicProduct\吉他谱\晴天.gp4")
print("song attrs:", [a for a in dir(song) if not a.startswith("_")])
for n in ["tempo", "measureHeaders", "tracks"]:
    v = getattr(song, n, None)
    print("song.", n, "=", v if n != "tracks" else [t.name for t in v])
print("note attrs:", [a for a in dir(song.tracks[1].measures[0].voices[0].beats[0].notes[0]) if not a.startswith("_")])

# 每轨道: 每 beat 音符数分布 + 前几个音符 (string, value)
for ti, t in enumerate(song.tracks):
    from collections import Counter
    cnt = Counter()
    samples = []
    for m in t.measures:
        for v in m.voices:
            for b in v.beats:
                cnt[len(b.notes)] += 1
                if len(samples) < 6 and len(b.notes) >= 3:
                    samples.append([(n.string, n.value) for n in b.notes])
    print(f"\n轨道{ti} {t.name!r}: beat音符数分布 {dict(cnt)}")
    for s in samples[:4]:
        print("   弦/值:", s)
