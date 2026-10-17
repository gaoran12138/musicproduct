# -*- coding: utf-8 -*-
"""解析 晴天.gp4: 结构、速度、调号、各轨道的和弦事件"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import guitarpro

song = guitarpro.parse(r"D:\musicProduct\吉他谱\晴天.gp4")
print("曲名:", song.title, "| 艺术家:", song.artist)
print("轨道数:", len(song.tracks))
for t in song.tracks:
    print(f"  轨道: {t.name!r} | 小节数: {len(t.measures)}")

# 速度与调号 (从第一个有信息的 header 取)
first = song.tracks[0].measures[0]
print("\n首小节: tempo:", getattr(first.header, "tempo", None),
      "| 拍号:", getattr(first.header, "time_signature", None),
      "| 调号:", getattr(first.header, "key_signature", None))

# 各轨道小节数 + 和弦事件统计
for t in song.tracks:
    nchords = 0
    chord_names = set()
    for m in t.measures:
        for v in m.voices:
            for b in v.beats:
                if b.chord is not None and b.chord.name:
                    nchords += 1
                    chord_names.add(b.chord.name)
    print(f"\n轨道 {t.name!r}: 和弦事件 {nchords} 个 | 用到和弦: {sorted(chord_names)}")
