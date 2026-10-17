# -*- coding: utf-8 -*-
"""按音高区间对比音准: 中低音区 vs 换声区 vs 高音区"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

y, sr = librosa.load(glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0], sr=22050, mono=True)
hop = 256
f0, flag, prob = librosa.pyin(y, fmin=80, fmax=800, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.6)
midi = np.full(len(f0), np.nan)
midi[ok] = 69 + 12*np.log2(f0[ok]/440.0)

# 音符切分
notes = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 3.0:
        j += 1
    if t[j]-t[i] >= 0.12:
        seg = midi[i:j+1]
        if np.percentile(seg, 90) - np.percentile(seg, 10) <= 0.8:   # 排除滑音
            notes.append((float(np.median(seg)), t[j]-t[i]))
    i = j+1

midis = np.array([m for m, _ in notes])
devs = (midis - np.round(midis)) * 100
ranges = [("低音区 < C4 (MIDI<60)", midis < 60),
          ("中音区 C4~D#4 (60-63)", (midis >= 60) & (midis < 64)),
          ("换声区 E4~G4 (64-67)", (midis >= 64) & (midis < 68)),
          ("高音区 >= G#4 (68+)", midis >= 68)]
print(f"总稳定音符 {len(notes)} 个\n")
print(f"{'音区':28s} {'音符数':>6s} {'偏差中位':>9s} {'平均绝对偏差':>12s} {'±25内':>7s}")
for label, m in ranges:
    if m.sum() >= 3:
        d = np.abs(devs[m])
        print(f"{label:28s} {m.sum():6d} {np.median(d):8.1f}音分 {np.mean(d):11.1f}音分 {(d<25).mean()*100:6.1f}%")
    else:
        print(f"{label:28s} {m.sum():6d}  (样本太少)")

# 长音 vs 短音
longs = np.array([d for (m, d) in notes]) >= 0.5
print(f"\n长音(>=0.5s): {longs.sum()} 个, 偏差中位 {np.median(np.abs(devs[longs])):.1f} 音分")
print(f"短音(<0.5s) : {(~longs).sum()} 个, 偏差中位 {np.median(np.abs(devs[~longs])):.1f} 音分")
