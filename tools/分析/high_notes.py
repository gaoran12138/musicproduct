# -*- coding: utf-8 -*-
"""找出录音里的最高音段落, 并判断是真声(胸声)还是假声/混声"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

VOX = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0]
y, sr = librosa.load(VOX, sr=22050, mono=True)
hop = 256
f0, flag, prob = librosa.pyin(y, fmin=80, fmax=900, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.6)
midi = np.full(len(f0), np.nan)
midi[ok] = 69 + 12 * np.log2(f0[ok] / 440.0)

names = {0:"C",1:"C#",2:"D",3:"D#",4:"E",5:"F",6:"F#",7:"G",8:"G#",9:"A",10:"A#",11:"B"}
def nm(m):
    mi = int(round(m)); return f"{names[mi%12]}{mi//12-1}(MIDI {mi}, {440*2**((mi-69)/12):.0f}Hz)"

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
        notes.append((t[i], t[j], float(np.median(midi[i:j+1])), t[j]-t[i]))
    i = j+1

notes_sorted = sorted(notes, key=lambda x: -x[2])
print("=== 最高的 12 个音 ===")
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
for a, b, m, d in notes_sorted[:12]:
    ia, ib = int(a*sr/hop), int(b*sr/hop)
    seg = S[:, ia:ib+1].mean(axis=1)
    f0h = 440 * 2**((round(m)-69)/12)
    # 谐波能量占比: 前3个谐波 vs 全谱 (真声谐波丰富, 假声/气声弱)
    def band_energy(center, w=40):
        m_ = (fr >= center-w) & (fr <= center+w)
        return seg[m_].sum() if m_.any() else 0.0
    h12 = band_energy(f0h) + band_energy(2*f0h)
    tot = seg.sum() + 1e-9
    # 高频泛音(3-5次)占比 -> 胸声更亮
    hi = sum(band_energy(k*f0h) for k in (3,4,5))
    cent = float((fr*seg).sum()/tot)
    print(f"  {a:6.1f}s  {nm(m):22s} 时长{d:4.2f}s | 基频+2次谐波占比 {h12/tot*100:5.1f}% | 3-5次 {hi/tot*100:4.1f}% | 谱质心 {cent:6.0f}Hz")

# 高音区(E4 以上)的整体特征
E4 = 64
hi_mask = ok & (midi >= E4)
print(f"\n=== 高音区统计 (E4 及以上, MIDI>=64) ===")
print(f"  高音区帧数占比: {hi_mask.sum()/max(ok.sum(),1)*100:.1f}%  |  时长 {hi_mask.sum()*hop/sr:.1f}s")
for thr, label in ((67, "G4"), (69, "A4"), (71, "B4")):
    m_ = ok & (midi >= thr)
    if m_.sum():
        seg = (t[m_][-1] - t[m_][0])
        print(f"  >= {label}(MIDI {thr}): {m_.sum()*hop/sr:.1f}s  ({m_.sum()/max(ok.sum(),1)*100:.1f}% 的有声时长)")
    else:
        print(f"  >= {label}(MIDI {thr}): 0s (没唱到)")

# 最高音的颤音稳定性 (挤压/硬顶会表现为音高不稳)
print(f"\n=== 最高音段落稳定性 ===")
for a, b, m, d in notes_sorted[:5]:
    idx = (t >= a) & (t <= b) & ok
    seg = midi[idx]
    if len(seg) > 3:
        print(f"  {a:6.1f}s {nm(m):20s} 音高波动(标准差) {np.std(seg)*100:5.0f} 音分")
