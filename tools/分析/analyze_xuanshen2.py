# -*- coding: utf-8 -*-
"""逐帧分析: 找出他真正"唱"的片段, 判断高音是混声还是假声"""
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
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"
hz = lambda m: 440*2**((round(m)-69)/12)

S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
rms = librosa.feature.rms(S=S)[0]
n = min(len(f0), S.shape[1], len(rms))

print(f"人声轨时长 {len(y)/sr:.1f}s | 有效音高帧 {ok[:n].sum()} ({ok[:n].mean()*100:.1f}%)")

# 逐帧音区统计 (帧加权)
sel = ok[:n]
print(f"\n=== 音高分布 (帧加权) ===")
ms = midi[:n][sel]
for base in range(48, 90, 2):
    s = (ms >= base) & (ms < base+2)
    if s.sum():
        print(f"  {nm(base):>4s}: {'█'*max(int(s.sum()*hop/sr*4),1)} {s.sum()*hop/sr:5.1f}s")

# 高音段逐帧谐波分析: 只统计响度较大的帧(排除弱帧/噪声)
print(f"\n=== 高声区逐帧谐波特征 (判断混声/假声) ===")
print(f"{'音区':>10s} {'时长s':>7s} {'1-2次谐波占比':>12s} {'3-6次占比':>10s}  判断")
lo_th = np.percentile(rms[:n][sel], 40) if sel.sum() else 0
rows = []
for base in range(60, 86):
    idx = np.where(sel & (np.abs(midi[:n]-base) < 0.5) & (rms[:n] > lo_th))[0]
    if len(idx) < 3:
        continue
    lo_sum, hi_sum, tot = 0.0, 0.0, 0.0
    for k in idx:
        f = hz(base)
        spec = S[:, k]; tt = spec.sum()+1e-9
        e = lambda c, w=45: (spec[(fr>=c-w)&(fr<=c+w)].sum() if ((fr>=c-w)&(fr<=c+w)).any() else 0)
        lo_sum += e(f)+e(2*f); hi_sum += sum(e(j*f) for j in (3,4,5,6)); tot += tt
    lr = lo_sum/tot; hr = hi_sum/tot
    zone = "混声/胸声(有芯)" if hr/max(lr,1e-9) > 0.25 else ("偏假声(泛音少)" if lr > 0.6 else "中间态")
    mark = "  ★ C5" if base == 72 else ""
    print(f"{nm(base):>10s} {len(idx)*hop/sr:6.1f}s {lr*100:11.1f}% {hr*100:9.1f}%  {zone}{mark}")

# 找最高的"有芯"帧(混声上限)
print(f"\n=== 混声上限估计 ===")
best = None
for k in np.where(sel & (rms[:n] > lo_th))[0]:
    f = hz(round(midi[k]))
    spec = S[:, k]; tt = spec.sum()+1e-9
    e = lambda c, w=45: (spec[(fr>=c-w)&(fr<=c+w)].sum() if ((fr>=c-w)&(fr<=c+w)).any() else 0)
    lr = (e(f)+e(2*f))/tt; hr = sum(e(j*f) for j in (3,4,5,6))/tt
    if hr/max(lr,1e-9) > 0.3 and lr < 0.65:      # 有芯特征
        if best is None or midi[k] > best[0]:
            best = (midi[k], t[k], lr, hr)
if best:
    print(f"  最高'有芯'(混声特征)帧: {nm(best[0])} ({hz(round(best[0])):.0f}Hz) 于 {best[1]:.1f}s | 1-2次{best[2]*100:.0f}% 3-6次{best[3]*100:.0f}%")
else:
    print("  未找到明显的混声特征帧")

print(f"\n=== 所有 A4(440Hz) 以上的高音帧片段 ===")
high = np.where(sel & (midi[:n] >= 69))[0]
if len(high):
    groups = []
    cur = [high[0]]
    for k in high[1:]:
        if k - cur[-1] <= 3: cur.append(k)
        else: groups.append(cur); cur = [k]
    groups.append(cur)
    for g in groups:
        if len(g) * hop/sr < 0.08: continue
        mm = np.median(midi[:n][g])
        f = hz(round(mm))
        lo_s = hi_s = tot = 0.0
        for k in g:
            spec = S[:, k]; tot += spec.sum()+1e-9
            e = lambda c, w=45: (spec[(fr>=c-w)&(fr<=c+w)].sum() if ((fr>=c-w)&(fr<=c+w)).any() else 0)
            lo_s += e(f)+e(2*f); hi_s += sum(e(j*f) for j in (3,4,5,6))
        lr = lo_s/tot; hr = hi_s/tot
        zone = "混声/胸声" if hr/max(lr,1e-9) > 0.25 else ("假声/气声" if lr > 0.6 else "中间")
        print(f"  {t[g[0]]:6.1f}s~{t[g[-1]]:6.1f}s ({len(g)*hop/sr:4.2f}s) {nm(mm):>4s} ({f:5.0f}Hz) 1-2次{lr*100:4.0f}% 3-6次{hr*100:4.0f}% -> {zone}")
else:
    print("  无 A4 以上的帧")
