# -*- coding: utf-8 -*-
"""分析 GP4 吉他1 的右手节奏: 每小节每拍弹了几根弦(扫弦=多弦, 分解=单弦)"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import guitarpro

song = guitarpro.parse(r"D:\musicProduct\吉他谱\晴天.gp4")
gt = song.tracks[1]
headers = song.measureHeaders
TICKS_PER_Q = 960  # 四分音符
SCALE = 269.75 / (headers[-1].start + headers[-1].length)

def beats_of_measure(m):
    """返回 [(start_ticks_in_measure, [strings]), ...]"""
    out = []
    for v in m.voices:
        for b in v.beats:
            if not b.notes:
                continue
            strings = sorted(n.string for n in b.notes)
            out.append((b.startInMeasure if b.startInMeasure is not None else b.start % 3840, strings))
    return out

# 采样几个区域: 前奏(0-8), 主歌(8-20), 副歌(40-54)
for mi in list(range(0, 8)) + list(range(8, 16)) + list(range(40, 48)):
    m = gt.measures[mi]
    bts = beats_of_measure(m)
    # 按 16 分位网格排列
    grid = ["."] * 16
    for start, strings in bts:
        pos = int(round(start / 240))  # 16分音符=240ticks
        if 0 <= pos < 16:
            grid[pos] = str(len(strings))
    print(f"m{mi:2d} [{''.join(grid)}]  (数字=该16分位弹的弦数, .=休止)")
