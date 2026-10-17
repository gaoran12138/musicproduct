# -*- coding: utf-8 -*-
"""按音区统计颤音速率与深度 (检验各音区是否都自然)"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"
p = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0]
y, sr = librosa.load(p, sr=22050, mono=True)
hop = 128
f0, flag, prob = librosa.pyin(y, fmin=70, fmax=800, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.6)
midi = np.full(len(f0), np.nan)
midi[ok] = 69 + 12*np.log2(f0[ok]/440.0)

res = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 4.0:
        j += 1
    d = t[j]-t[i]
    if d >= 0.45 and (j-i+1) >= 35:
        seg = midi[i:j+1]*100
        x = seg - np.linspace(seg[0], seg[-1], len(seg)); x = x - x.mean()
        sp = np.abs(np.fft.rfft(x*np.hanning(len(x))))
        frq = np.fft.rfftfreq(len(x), d=(t[1]-t[0]))
        bd = (frq >= 3) & (frq <= 9)
        if bd.sum():
            res.append((float(np.median(midi[i:j+1])), frq[bd][np.argmax(sp[bd])],
                        2*np.sqrt(2)*np.std(x), d, nm(float(np.median(midi[i:j+1])))))
    i = j+1

R = res
print(f"长音(>=0.45s) 共 {len(R)} 个\n")
hdr = f"{'音区':>14s} {'个数':>4s} {'速率中位':>9s} {'深度中位':>9s}"
print(hdr)
for lab, lo, hi in (("低 <C4", 0, 60), ("中 C4~D#4", 60, 64), ("换声 E4~G4", 64, 68), ("高 >=G#4", 68, 200)):
    s = [r for r in R if lo <= r[0] < hi]
    if len(s) >= 2:
        rate = np.median([r[1] for r in s]); dep = np.median([r[2] for r in s])
        print(f"{lab:>14s} {len(s):4d} {rate:7.1f}Hz {dep:7.0f}音分")
    else:
        print(f"{lab:>14s} {len(s):4d}   样本不足")

print("\n全部长音明细 (音名 / 时长 / 速率 / 深度):")
for m, rate, dep, d, name in sorted(R, key=lambda x: x[0]):
    flag_ = "⚠️无颤音" if dep < 15 else ("✓" if 3 <= rate <= 8 else "速率异常")
    print(f"  {name:>4s} {d:4.2f}s  {rate:5.1f}Hz  {dep:5.0f}音分  {flag_}")
