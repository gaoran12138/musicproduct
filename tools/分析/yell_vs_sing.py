# -*- coding: utf-8 -*-
"""区分"喊"和"唱": 高音帧的噪声度/响度/抖动 vs 中低音帧"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

p = glob.glob(r"D:\musicProduct\分轨\炫神_分轨\*(Vocals)*.wav")[0]
y, sr = librosa.load(p, sr=22050, mono=True)
hop = 256
f0, flag, prob = librosa.pyin(y, fmin=60, fmax=1500, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.5)
midi = np.full(len(f0), np.nan); midi[ok] = 69+12*np.log2(f0[ok]/440.0)

S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
# 谱平坦度(噪声度): 高 = 噪声/沙哑(喊), 低 = 谐波清晰(唱)
flat = librosa.feature.spectral_flatness(S=S)[0]
rms = librosa.feature.rms(S=S)[0]
n = min(len(f0), len(flat), len(rms))

# 音高抖动(帧间变化)
jit = np.full(n, np.nan)
d = np.abs(np.diff(midi[:n]))
jit[1:] = d

print(f"{'音区':>14s} {'时长s':>7s} {'RMS':>8s} {'谱平坦度':>10s} {'音高抖动':>9s}")
bands = [("说话区 C3~B3", 48, 60), ("中音 C4~G4", 60, 68), ("高音 G#4~C5", 68, 73), ("超高 D5 以上", 74, 100)]
for lab, lo, hi in bands:
    sel = ok[:n] & (midi[:n] >= lo) & (midi[:n] < hi) & (rms[:n] > np.percentile(rms[:n], 20))
    if sel.sum() >= 5:
        print(f"{lab:>14s} {sel.sum()*hop/sr:6.1f}s {rms[:n][sel].mean():8.4f} {np.median(flat[:n][sel]):10.4f} {np.nanmedian(jit[:n][sel]):8.3f}")
    else:
        print(f"{lab:>14s}   样本不足")

print()
print("参考: 喊声通常 = RMS高 + 谱平坦度高(噪声多) + 音高抖动大")
print("      训练过的混声 = RMS中等 + 谱平坦度低(谐波清晰) + 抖动小")
