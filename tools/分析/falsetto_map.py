# -*- coding: utf-8 -*-
"""假声区分析: 找出 C5 以上的音符 + 检查真假声之间的断层"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

y, sr = librosa.load(glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0], sr=22050, mono=True)
hop = 256
f0, flag, prob = librosa.pyin(y, fmin=80, fmax=1100, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.6)
midi = np.full(len(f0), np.nan)
midi[ok] = 69 + 12*np.log2(f0[ok]/440.0)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def nm(m):
    mi = int(round(m)); return f"{names[mi%12]}{mi//12-1}"

# 音符切分
notes = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 3.0:
        j += 1
    if t[j]-t[i] >= 0.10:
        notes.append((t[i], t[j], float(np.median(midi[i:j+1])), t[j]-t[i]))
    i = j+1

# 音高直方图 (半音粒度)
allm = np.array([m for _,_,m,_ in notes])
print("=== 各音区音符统计 (按 MIDI) ===")
for lo in range(48, 84, 4):
    m_ = (allm >= lo) & (allm < lo+4)
    if m_.sum():
        bar = "█" * int(m_.sum() / 2)
        print(f"  {nm(lo):>4s}~{nm(lo+3):<4s} ({lo}-{lo+3}): {m_.sum():3d} 个 {bar}")

print("\n=== C5 (MIDI 72) 以上的音符 ===")
hi = [n for n in notes if n[2] >= 72]
hi.sort(key=lambda x: -x[2])
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
if hi:
    print(f"数量: {len(hi)} | 总时长: {sum(x[3] for x in hi):.2f}s")
    for a, b, m, d in hi:
        ia, ib = int(a*sr/hop), int(b*sr/hop)
        seg = S[:, ia:ib+1].mean(axis=1)
        f0h = 440*2**((round(m)-69)/12)
        tot = seg.sum()+1e-9
        def e(c, w=40):
            m_ = (fr>=c-w)&(fr<=c+w); return seg[m_].sum() if m_.any() else 0
        print(f"  {a:6.1f}s  {nm(m):4s} ({f0h:5.0f}Hz) 时长{d:4.2f}s | 基频占比 {e(f0h)/tot*100:4.1f}% | 2次 {e(2*f0h)/tot*100:4.1f}% | 3-5次 {sum(e(k*f0h) for k in (3,4,5))/tot*100:4.1f}%")
else:
    print("  无")

print("\n=== 换声断层检查 (A4~C5, MIDI 69-71) ===")
gap = [n for n in notes if 69 <= n[2] < 72]
print(f"  A4~B4 音符数: {len(gap)} | 总时长: {sum(x[3] for x in gap):.2f}s")
if gap:
    for a,b,m,d in gap[:6]:
        print(f"    {a:6.1f}s {nm(m):4s} 时长{d:.2f}s")

print("\n=== 结论数据 ===")
if hi:
    top = max(hi, key=lambda x: x[2])
    print(f"  假声最高音: {nm(top[2])} ({440*2**((round(top[2])-69)/12):.0f}Hz) 于 {top[0]:.1f}s, 时长 {top[3]:.2f}s")
    print(f"  假声区(C5+)总时长: {sum(x[3] for x in hi):.2f}s / 全长 {len(y)/sr:.0f}s")
chest = [n for n in notes if n[2] < 69]
if chest:
    top_chest = max(chest, key=lambda x: x[2] if x[3] >= 0.4 else 0)
    print(f"  真声持续最高(>=0.4s): {nm(top_chest[2])} ({440*2**((round(top_chest[2])-69)/12):.0f}Hz)")
