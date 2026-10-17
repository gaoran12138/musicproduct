# -*- coding: utf-8 -*-
"""验证高音真实性: 列出最高音符 + 谐波结构 (排除口哨/异响)"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

path, label = sys.argv[1], sys.argv[2]
y, sr = librosa.load(path, sr=22050, mono=True)
hop = 256
f0, flag, prob = librosa.pyin(y, fmin=70, fmax=1400, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.55)
midi = np.full(len(f0), np.nan); midi[ok] = 69+12*np.log2(f0[ok]/440.0)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"
hz = lambda m: 440*2**((round(m)-69)/12)

notes = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 5.0:
        j += 1
    if t[j]-t[i] >= 0.10:
        notes.append((t[i], t[j], float(np.median(midi[i:j+1])), t[j]-t[i]))
    i = j+1

S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)); fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
print(f"===== {label} 最高 12 个音 =====")
for a, b, m, d in sorted(notes, key=lambda x: -x[2])[:12]:
    ia, ib = int(a*sr/hop), int(b*sr/hop)
    seg = S[:, ia:ib+1].mean(axis=1); tot = seg.sum()+1e-9
    e = lambda c, w=45: (seg[(fr>=c-w)&(fr<=c+w)].sum() if ((fr>=c-w)&(fr<=c+w)).any() else 0)
    f = hz(round(m))
    h = [e(k*f)/tot for k in (1,2,3,4,5)]
    tag = "真声/胸声" if (h[2]+h[3]+h[4])/max(h[0]+h[1],1e-9) > 0.15 else ("假声/气声" if h[0]+h[1] > 0.4 else "异响?")
    print(f"  {a:6.1f}s {nm(m):>4s}({hz(round(m)):5.0f}Hz) {d:4.2f}s 谐波1-5: " +
          " ".join(f"{x*100:4.1f}%" for x in h) + f"  -> {tag}")

print(f"\n===== {label} 最低 8 个音 =====")
for a, b, m, d in sorted(notes, key=lambda x: x[2])[:8]:
    print(f"  {a:6.1f}s {nm(m):>4s}({hz(round(m)):5.0f}Hz) 时长{d:4.2f}s 偏差{(m-round(m))*100:+5.0f}音分")
