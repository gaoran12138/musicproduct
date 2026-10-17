# -*- coding: utf-8 -*-
"""炫神人声分析: 音域分布 + 换声点定位 + C5 是混声还是假声"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

p = glob.glob(r"D:\musicProduct\分轨\炫神_分轨\*(Vocals)*.wav")[0]
y, sr = librosa.load(p, sr=22050, mono=True)
print(f"人声轨: {p.split(chr(92))[-1]} | 时长 {len(y)/sr:.1f}s | RMS {20*np.log10(np.sqrt(np.mean(y**2))+1e-9):.1f}dB")

hop = 256
f0, flag, prob = librosa.pyin(y, fmin=60, fmax=1500, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.55)
midi = np.full(len(f0), np.nan); midi[ok] = 69+12*np.log2(f0[ok]/440.0)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"
hz = lambda m: 440*2**((round(m)-69)/12)

S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
fr = librosa.fft_frequencies(sr=sr, n_fft=2048)

notes = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 5.0:
        j += 1
    d = t[j]-t[i]
    if d >= 0.12:
        seg = midi[i:j+1]; m = float(np.median(seg))
        spec = S[:, i:j+1].mean(axis=1); tot = spec.sum()+1e-9
        f = hz(round(m))
        e = lambda c, w=45: (spec[(fr>=c-w)&(fr<=c+w)].sum() if ((fr>=c-w)&(fr<=c+w)).any() else 0)
        low_h = e(f)+e(2*f); high_h = sum(e(k*f) for k in (3,4,5,6))
        notes.append((t[i], d, m, high_h/(low_h+1e-9), (low_h)/tot, float(np.std(seg)*100)))
    i = j+1

N = notes
print(f"\n切出音符 {len(N)} 个 | 总发声 {sum(n[1] for n in N):.1f}s")
ms = np.array([n[2] for n in N]); ds = np.array([n[1] for n in N]); rich = np.array([n[3] for n in N])
print(f"音域: {nm(ms.min())}({hz(ms.min()):.0f}Hz) ~ {nm(ms.max())}({hz(ms.max()):.0f}Hz) | 跨度 {ms.max()-ms.min():.1f} 半音")
print(f"常用(25-75%): {nm(np.percentile(ms,25))} ~ {nm(np.percentile(ms,75))}")

print(f"\n=== 音高分布 (时长加权) ===")
for base in range(int(ms.min())//2*2, int(ms.max())+1, 2):
    sel = (ms >= base) & (ms < base+2)
    if sel.sum():
        print(f"  {nm(base):>4s}: {'█'*max(int(ds[sel].sum()*6),1)} {ds[sel].sum():5.1f}s")

print(f"\n=== 逐音: 泛音丰富度 (判断声区) ===")
print(f"{'音名':>5s} {'时长':>6s} {'泛音比':>8s} {'1-2次谐波占比':>12s} {'波动':>6s}  声区判断")
for base in range(int(ms.min())//1, int(ms.max())+1):
    sel = np.abs(ms-base) < 0.5
    if sel.sum() >= 1:
        r = float(np.average(rich[sel], weights=ds[sel]))
        lo = float(np.average(np.array([n[4] for n in N])[sel], weights=ds[sel]))
        w = ds[sel].sum()
        # 判断: 1-2次谐波占比高 + 泛音比低 => 假声/气声; 反之胸/混声
        zone = "混声/胸声(有芯)" if (r > 0.4 or lo < 0.6) else ("偏假声(泛音少)" if lo > 0.7 else "中间态")
        mark = " ★C5" if base == 72 else ""
        print(f"{nm(base):>5s} {w:5.1f}s {r:8.2f} {lo*100:11.1f}% {np.average(np.array([n[5] for n in N])[sel], weights=ds[sel]):6.0f}  {zone}{mark}")
