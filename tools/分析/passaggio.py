# -*- coding: utf-8 -*-
"""定位换声点: 逐音高统计音色/稳定性指标, 找突变位置"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

path = sys.argv[1]
y, sr = librosa.load(path, sr=22050, mono=True)
hop = 256
f0, flag, prob = librosa.pyin(y, fmin=70, fmax=1200, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.55)
midi = np.full(len(f0), np.nan); midi[ok] = 69+12*np.log2(f0[ok]/440.0)
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"

# 逐音符指标
rows = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.5 and (t[j+1]-t[i]) < 5.0:
        j += 1
    d = t[j]-t[i]
    if d >= 0.15:
        seg = midi[i:j+1]
        m = float(np.median(seg))
        ia, ib = i, j+1
        spec = S[:, ia:ib].mean(axis=1)
        tot = spec.sum()+1e-9
        cent = float((fr*spec).sum()/tot)
        # 谐波丰富度: 3-5 次谐波 / 1-2 次
        f = 440*2**((round(m)-69)/12)
        e = lambda c, w=45: (spec[(fr>=c-w)&(fr<=c+w)].sum() if ((fr>=c-w)&(fr<=c+w)).any() else 0)
        low_h = e(f)+e(2*f); high_h = sum(e(k*f) for k in (3,4,5))
        rich = high_h/(low_h+1e-9)
        # HNR
        a, b = int(t[i]*sr), int(t[j]*sr)
        segw = y[a:b] - y[a:b].mean() if b-a > 1024 else None
        hnr = np.nan
        if segw is not None:
            ac = np.correlate(segw, segw, "full")[len(segw)-1:]
            ac = ac/(ac[0]+1e-12)
            lo, hi = max(int(sr/1000), 2), int(sr/70)
            if hi < len(ac):
                r = ac[lo:hi].max()
                if 0 < r < 1: hnr = 10*np.log10(r/(1-r))
        rms = float(np.sqrt(np.mean(y[a:b]**2))) if b > a else 0
        rows.append((m, d, cent, rich, hnr, float(np.std(seg)*100), rms))
    i = j+1

rows = np.array([r for r in rows if not np.isnan(r[4])], dtype=float)
print(f"有效音符 {len(rows)} 个\n")
print(f"{'音名':>5s} {'时长s':>6s} {'质心Hz':>7s} {'泛音比':>7s} {'HNRdB':>6s} {'波动音分':>8s} {'RMS':>7s}")
for base in range(int(rows[:,0].min()), int(rows[:,0].max())+1):
    sel = np.abs(rows[:,0]-base) < 0.5
    if sel.sum() >= 2:
        r = rows[sel]
        w = r[:,1]
        f = lambda c: np.average(r[:,c], weights=w)
        print(f"{nm(base):>5s} {w.sum():6.1f} {f(2):7.0f} {f(3):7.2f} {f(4):6.1f} {f(5):8.0f} {f(6):7.4f}")
