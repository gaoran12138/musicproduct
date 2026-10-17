# -*- coding: utf-8 -*-
"""假声测试分析: 范围 / 上限 / 下限 / 稳定性 / 谐波真实性(排除假象)"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

y, sr = librosa.load(r"D:\musicProduct\素材\转换中间\falsetto_test.wav", sr=22050, mono=True)
dur = len(y)/sr
rms = float(np.sqrt(np.mean(y**2)))
print(f"时长 {dur:.1f}s | RMS {rms:.4f} ({20*np.log10(rms+1e-9):.1f} dBFS) | 峰值 {np.abs(y).max():.3f}")

hop = 256
f0, flag, prob = librosa.pyin(y, fmin=100, fmax=1400, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.5)
print(f"有声帧占比: {ok.mean()*100:.1f}%")

names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def nm(m):
    mi = int(round(m)); return f"{names[mi%12]}{mi//12-1}"
def hz(m): return 440*2**((m-69)/12)

midi = np.full(len(f0), np.nan)
midi[ok] = 69 + 12*np.log2(f0[ok]/440.0)

# 音符切分
notes = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.7 and (t[j+1]-t[i]) < 4.0:
        j += 1
    d = t[j]-t[i]
    if d >= 0.08:
        seg = midi[i:j+1]
        notes.append((t[i], t[j], float(np.median(seg)), d, float(np.std(seg)*100)))
    i = j+1

S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
def harm_ratio(a, b, m):
    ia, ib = int(a*sr/hop), int(b*sr/hop)
    seg = S[:, ia:ib+1].mean(axis=1)
    f0h = hz(round(m))
    tot = seg.sum()+1e-9
    def e(c, w=45):
        m_ = (fr>=c-w)&(fr<=c+w); return seg[m_].sum() if m_.any() else 0
    h = [e(k*f0h) for k in (1,2,3,4)]
    return (h[0]+h[1])/tot, sum(h[2:])/tot

print(f"\n音符数: {len(notes)}")
print(f"{'时间':>7s} {'音名':>5s} {'频率':>7s} {'时长':>5s} {'波动':>7s} {'基频+2次占比':>11s} {'3-4次':>7s}")
for a, b, m, d, sd in sorted(notes, key=lambda x: -x[2])[:18]:
    h12, h34 = harm_ratio(a, b, m)
    print(f"{a:6.1f}s {nm(m):>5s} {hz(round(m)):6.0f}Hz {d:4.2f}s {sd:6.0f}音分 {h12*100:10.1f}% {h34*100:6.1f}%")

# 统计
if notes:
    ms = np.array([m for _,_,m,_,_ in notes])
    ds = np.array([d for _,_,_,d,_ in notes])
    # 用时长加权的音高分布
    print(f"\n=== 范围 ===")
    print(f"  最高音: {nm(ms.max())} ({hz(round(ms.max())):.0f}Hz)")
    print(f"  最低音: {nm(ms.min())} ({hz(round(ms.min())):.0f}Hz)")
    print(f"  跨幅: {ms.max()-ms.min():.1f} 半音")
    print(f"  时长加权平均音: {nm(np.average(ms, weights=ds))}")
    # 音高直方图
    print(f"\n=== 音高分布(半音) ===")
    for base in range(60, 88, 2):
        m_ = (ms >= base) & (ms < base+2)
        if m_.sum():
            print(f"  {nm(base):>4s}~{nm(base+1):<4s}: {'█'*int(ds[m_].sum()*8)}  {ds[m_].sum():.1f}s")

# 真假声衔接: 检查音高轨迹是否有连续滑音(而非断层)
dmidi = np.abs(np.gradient(midi[ok])) if ok.sum() > 10 else np.array([])
if len(dmidi):
    gliss = (dmidi > 0.05).mean()
    print(f"\n=== 换声连续性 ===")
    print(f"  音高在变化中的帧占比: {gliss*100:.1f}%  (>25% 说明有较多滑音/连续过渡)")
    print(f"  相邻帧平均音高变化: {np.mean(dmidi):.3f} 半音")
