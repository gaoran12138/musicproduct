# -*- coding: utf-8 -*-
"""按音长拆分音准误差 (长音才是被听到的音)"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

targets = [
    (glob.glob(r"D:\musicProduct\分轨\录音33_分轨\*(Vocals)*.wav")[0], "你的《大人中》翻唱"),
    (glob.glob(r"D:\musicProduct\分轨\原曲大人中_分轨\*(Vocals)*.wav")[0], "原曲《大人中》"),
]

for path, lab in targets:
    y, sr = librosa.load(path, sr=22050, mono=True)
    hop = 256
    f0, flag, prob = librosa.pyin(y, fmin=60, fmax=900, sr=sr, frame_length=2048, hop_length=hop)
    t = librosa.times_like(f0, sr=sr, hop_length=hop)
    ok = (~np.isnan(f0)) & flag & (prob > 0.6)
    midi = np.full(len(f0), np.nan)
    midi[ok] = 69 + 12*np.log2(f0[ok]/440.0)

    notes = []
    i = 0
    while i < len(midi):
        if np.isnan(midi[i]):
            i += 1; continue
        j = i
        while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 4.0:
            j += 1
        d = t[j]-t[i]
        if d >= 0.15:
            seg = midi[i:j+1]
            if np.std(seg) <= 60:
                notes.append((d, float(np.median(seg))))
        i = j+1

    N = np.array(notes)
    dv = np.abs((N[:, 1]-np.round(N[:, 1]))*100)
    print(f"===== {lab} =====")
    print(f"{'音长分组':>14s} {'个数':>5s} {'偏差中位':>9s} {'平均':>8s} {'>25音分':>8s}")
    groups = [("长音 >=0.5s", N[:, 0] >= 0.5),
              ("中音 0.3~0.5s", (N[:, 0] >= 0.3) & (N[:, 0] < 0.5)),
              ("短音 <0.3s", N[:, 0] < 0.3)]
    for g, sel in groups:
        if sel.sum() >= 3:
            print(f"{g:>14s} {sel.sum():5d} {np.median(dv[sel]):8.1f} {np.mean(dv[sel]):8.1f} {100*(dv[sel]>25).mean():7.0f}%")
    print(f"{'全部':>14s} {len(N):5d} {np.median(dv):8.1f} {np.mean(dv):8.1f} {100*(dv>25).mean():7.0f}%")
    print()
