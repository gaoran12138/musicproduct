# -*- coding: utf-8 -*-
"""通用演唱分析: 传入 wav 路径, 输出音域/音准/颤音/气息/真假声分布"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

path = sys.argv[1]
label = sys.argv[2] if len(sys.argv) > 2 else path
y, sr = librosa.load(path, sr=22050, mono=True)
dur = len(y)/sr
rms = float(np.sqrt(np.mean(y**2)))
print(f"===== {label} =====")
print(f"时长 {dur:.1f}s | RMS {20*np.log10(rms+1e-9):.1f} dBFS | 峰值 {np.abs(y).max():.3f}")

hop = 256
f0, flag, prob = librosa.pyin(y, fmin=70, fmax=1200, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.55)
if ok.sum() < 50:
    print("有效人声太少, 跳过")
    sys.exit()
midi = np.full(len(f0), np.nan)
midi[ok] = 69 + 12*np.log2(f0[ok]/440.0)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"
hz = lambda m: 440*2**((round(m)-69)/12)

# 音符
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
def harm(a, b, m):
    ia, ib = int(a*sr/hop), int(b*sr/hop)
    if ib <= ia: return 0, 0
    seg = S[:, ia:ib+1].mean(axis=1); tot = seg.sum()+1e-9
    e = lambda c, w=45: (seg[(fr>=c-w)&(fr<=c+w)].sum() if ((fr>=c-w)&(fr<=c+w)).any() else 0)
    f = hz(round(m))
    return (e(f)+e(2*f))/tot, sum(e(k*f) for k in (3,4,5))/tot

notes = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 4.0:
        j += 1
    d = t[j]-t[i]
    if d >= 0.12:
        seg = midi[i:j+1]
        h12, h34 = harm(t[i], t[j], np.median(seg))
        notes.append((t[i], t[j], float(np.median(seg)), d, float(np.std(seg)*100), h12, h34))
    i = j+1

if not notes:
    print("没切出音符")
    sys.exit()
ms = np.array([n[2] for n in notes]); ds = np.array([n[3] for n in notes])
print(f"音符数 {len(notes)} | 总发声 {ds.sum():.1f}s")

# 真实音符(有谐波, 排除异响)
real = np.array([n[6] > 0.005 or n[5] > 0.5 for n in notes])
print(f"谐波真实的音符: {real.sum()} / {len(notes)}")

print(f"\n【音域】")
print(f"  最高: {nm(ms[real].max())} ({hz(ms[real].max()):.0f}Hz) | 最低: {nm(ms[real].min())} ({hz(ms[real].min()):.0f}Hz)")
print(f"  跨幅: {ms[real].max()-ms[real].min():.1f} 半音 | 常用(25-75%): {nm(np.percentile(ms[real],25))} ~ {nm(np.percentile(ms[real],75))}")
print(f"  时长加权中心: {nm(np.average(ms[real], weights=ds[real]))}")

print(f"\n【音高分布】")
for base in range(int(ms[real].min()//2*2), int(ms[real].max())+1, 2):
    m_ = (ms >= base) & (ms < base+2) & real
    if m_.sum():
        print(f"  {nm(base):>4s}: {'█'*max(int(ds[m_].sum()*4),1)} {ds[m_].sum():.1f}s")

# 音准
devs = []
for a, b, m, d, sd, h12, h34 in notes:
    if sd > 80: continue
    devs.append((m - round(m))*100)
devs = np.array(devs)
print(f"\n【音准】(音符 {len(devs)} 个)")
print(f"  绝对偏差中位: {np.median(np.abs(devs)):.1f} 音分 | 平均 {np.mean(np.abs(devs)):.1f} | ±25内 {(np.abs(devs)<25).mean()*100:.1f}%")

# 分音区音准
print(f"\n【分音区音准】")
for lab, m_ in (("低 <C4", ms < 60), ("中 C4~D#4", (ms >= 60) & (ms < 64)), ("换声 E4~G4", (ms >= 64) & (ms < 68)), ("高 >=G#4", ms >= 68)):
    sel = m_ & real
    if sel.sum() >= 3:
        dd = np.array([abs((ms[k]-round(ms[k]))*100) for k in np.where(sel)[0]])
        print(f"  {lab:12s} {sel.sum():3d}个 偏差中位 {np.median(dd):5.1f}音分")

# 真假声分布 (用谐波丰富度判断: 胸声泛音多, 假声泛音少)
chest = np.array([n[6] > 0.06 for n in notes]) & real
fals = np.array([n[6] <= 0.06 for n in notes]) & real
print(f"\n【声区】")
if chest.sum():
    print(f"  胸声特征音符: {chest.sum()} 个 | 音域 {nm(ms[chest].min())}~{nm(ms[chest].max())} (泛音丰富)")
if fals.sum():
    print(f"  假声/气声特征: {fals.sum()} 个 | 音域 {nm(ms[fals].min())}~{nm(ms[fals].max())} (泛音稀少)")

# 颤音
rates = []
for a, b, m, d, sd, h12, h34 in notes:
    if d < 0.45: continue
    idx = (t >= a) & (t <= b) & ok
    seg = midi[idx]*100
    if len(seg) < 30: continue
    x = seg - np.linspace(seg[0], seg[-1], len(seg)); x = x - x.mean()
    sp = np.abs(np.fft.rfft(x*np.hanning(len(x)))); ff = np.fft.rfftfreq(len(x), d=(t[1]-t[0]))
    bd = (ff >= 3) & (ff <= 9)
    if bd.sum(): rates.append(ff[bd][np.argmax(sp[bd])])
if rates:
    print(f"\n【颤音】长音 {len(rates)} 个, 速率中位 {np.median(rates):.1f} Hz")

# 长音气息
drift = []
for a, b, m, d, sd, h12, h34 in notes:
    if d < 0.5: continue
    idx = (t >= a) & (t <= b) & ok
    seg = midi[idx]; k = max(len(seg)//3, 1)
    drift.append((np.mean(seg[-k:]) - np.mean(seg[:k]))*100)
if drift:
    print(f"【气息】长音 {len(drift)} 个, 首尾漂移中位 {np.median(drift):+.0f} 音分")
