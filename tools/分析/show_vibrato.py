# -*- coding: utf-8 -*-
"""提取一个长音, 用字符画出音高曲线, 展示颤音波形"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

path = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0]
y, sr = librosa.load(path, sr=22050, mono=True)
hop = 128   # 更细的时间分辨率
f0, flag, prob = librosa.pyin(y, fmin=70, fmax=800, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.6)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"

# 找最长的连续有声段
best = None
i = 0
while i < len(ok):
    if ok[i]:
        j = i
        while j+1 < len(ok) and ok[j+1] and abs(12*np.log2(f0[j+1]/f0[i])) < 1.0:
            j += 1
        if best is None or (j-i) > (best[1]-best[0]):
            best = (i, j)
        i = j+1
    else:
        i += 1

a, b = best
seg = 12*np.log2(f0[a:b+1]/440.0)      # 相对 A4 的半音数
midi_seg = seg + 69                     # 转 MIDI
ts = t[a:b+1]
mid = np.median(midi_seg)
m = round(mid)
print(f"最长稳定音: {nm(mid)} ({440*2**((m-69)/12):.0f}Hz)  |  时长 {ts[-1]-ts[0]:.2f}s  |  帧数 {len(seg)}")

# 去掉整体漂移, 只看振动
det = seg - np.linspace(seg[0], seg[-1], len(seg))
det = det - det.mean()
cents = det*100

# 字符曲线
chars = "▁▂▃▄▅▆▇█"
lo, hi = cents.min(), cents.max()
print(f"\n音高偏移曲线 (纵轴 {lo:.0f} ~ {hi:.0f} 音分):")
W = 100
step = max(len(cents)//W, 1)
line = ""
for k in range(0, len(cents), step):
    v = cents[k:k+step].mean()
    idx = int((v-lo)/(hi-lo+1e-9)*7)
    line += chars[idx]
print("  " + line)
print(f"  0s{'.'*int(len(line)*0.5)}中间{'.'*int(len(line)*0.4)}{ts[-1]-ts[0]:.1f}s")

# 颤音参数
x = cents
w = np.hanning(len(x))
sp = np.abs(np.fft.rfft(x*w))
fr = np.fft.rfftfreq(len(x), d=(ts[1]-ts[0]))
band = (fr >= 3) & (fr <= 9)
rate = fr[band][np.argmax(sp[band])] if band.sum() else 0
print(f"\n颤音速率: {rate:.1f} Hz  |  颤音深度(峰峰): {hi-lo:.0f} 音分  |  振幅(RMS): {np.std(cents):.0f} 音分")
print(f"平均音高: {nm(np.mean(midi_seg))}")
print()
print("解读: 波形规则=自然颤音; 4~7Hz 为理想; 峰峰值 30~100 音分为自然范围")
