# -*- coding: utf-8 -*-
"""对比三人高音区特征 (优化版: hop=512 + 帧采样)"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

cases = [
    (glob.glob(r"D:\musicProduct\分轨\周菲戈KissGoodbye_分轨\*(Vocals)*.wav")[0], "周菲戈(KissGoodbye)"),
    (glob.glob(r"D:\musicProduct\分轨\炫神_分轨\*(Vocals)*.wav")[0], "炫神(解说喊声)"),
    (glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0], "你(分裂)"),
]
hop = 512
hz = lambda m: 440*2**((round(m)-69)/12)

print(f"{'对象':>20s} {'音区':>13s} {'时长s':>7s} {'RMS':>8s} {'抖动':>7s} {'2次谐波':>8s}")
for path, lab in cases:
    y, sr = librosa.load(path, sr=22050, mono=True)
    f0, flag, prob = librosa.pyin(y, fmin=60, fmax=1500, sr=sr, frame_length=2048, hop_length=hop)
    t = librosa.times_like(f0, sr=sr, hop_length=hop)
    ok = (~np.isnan(f0)) & flag & (prob > 0.5)
    midi = np.full(len(f0), np.nan)
    midi[ok] = 69 + 12*np.log2(f0[ok]/440.0)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
    rms = librosa.feature.rms(S=S)[0]
    n = min(len(f0), len(rms), S.shape[1])
    jit = np.full(n, np.nan)
    jit[1:] = np.abs(np.diff(midi[:n]))

    for band, lo, hi in (("中音 C4~G4", 60, 68), ("高音 G#4~C5", 68, 73), ("换声 E4~G4", 64, 68)):
        sel = np.where(ok[:n] & (midi[:n] >= lo) & (midi[:n] < hi) & (rms[:n] > np.percentile(rms[:n], 30)))[0]
        if len(sel) < 5:
            print(f"{lab:>20s} {band:>13s}   样本不足")
            continue
        step = max(len(sel)//120, 1)
        sel_s = sel[::step]
        h2 = []
        for k in sel_s:
            f = hz(round(midi[k]))
            spec = S[:, k]; tot = spec.sum()+1e-9
            lo_i, hi_i = 2*f-50, 2*f+50
            m_ = (fr >= lo_i) & (fr <= hi_i)
            h2.append((spec[m_].sum() if m_.any() else 0)/tot)
        print(f"{lab:>20s} {band:>13s} {len(sel)*hop/sr:6.1f}s {rms[:n][sel].mean():8.4f} {np.nanmedian(jit[:n][sel]):7.3f} {np.median(h2)*100:7.1f}%")
    print()
