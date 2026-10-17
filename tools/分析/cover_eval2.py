# -*- coding: utf-8 -*-
"""翻唱评估 v2: 音符级音准 + 颤音谱 + 节奏对齐 (带合理性校验)"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

VOX = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0]
INST = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Instrumental)*.wav")[0]

yv, sr = librosa.load(VOX, sr=22050, mono=True)
yi, _ = librosa.load(INST, sr=22050, mono=True)
hop = 256
t = librosa.times_like(np.arange(1), sr=sr, hop_length=hop)  # placeholder

# ---- 合理性校验 ----
print("=== 校验 ===")
print(f"人声 RMS: {np.sqrt(np.mean(yv**2)):.4f} ({20*np.log10(np.sqrt(np.mean(yv**2))+1e-9):.1f} dBFS)")
print(f"伴奏 RMS: {np.sqrt(np.mean(yi**2)):.4f} ({20*np.log10(np.sqrt(np.mean(yi**2))+1e-9):.1f} dBFS)")

# ---- 音高轨迹 (pyin, 加置信度过滤) ----
f0, vflag, vprob = librosa.pyin(yv, fmin=80, fmax=800, sr=sr, frame_length=2048, hop_length=hop)
times = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & vflag & (vprob > 0.6)
print(f"有声且高置信帧: {ok.sum()} / {len(f0)} ({ok.mean()*100:.1f}%)")

f0v, tv = f0[ok], times[ok]
midi = 69 + 12 * np.log2(f0v / 440.0)

# 帧间跳变 (追踪质量/双重人声怀疑)
djump = np.abs(np.diff(midi))
print(f"帧间音高跳变 >1 半音 的比例: {(djump>1).mean()*100:.1f}%  (>15% 说明可能是两人声/追踪不稳)")

# ---- 音符切分 (音高稳定段) ----
notes = []   # (start, end, median_midi, duration)
i = 0
n = len(midi)
while i < n:
    j = i
    while j + 1 < n and abs(midi[j+1] - midi[i]) < 0.6 and (tv[j+1]-tv[i]) < 3.0:
        j += 1
    dur = tv[j] - tv[i]
    if dur >= 0.12 and len(midi[i:j+1]) >= 4:
        notes.append((tv[i], tv[j], float(np.median(midi[i:j+1])), dur))
    i = j + 1
print(f"\n=== 音符 ===")
print(f"切出音符数: {len(notes)} | 总发声时长 {sum(x[3] for x in notes):.1f}s")

# 音准: 音符中位音与最近十二平均律音的音分偏差 (排除滑音: 音符内音高波动大则跳过)
devs, slid = [], 0
for a, b, m, d in notes:
    seg = midi[(tv >= a) & (tv <= b)]
    if len(seg) < 4:
        continue
    if np.percentile(seg, 90) - np.percentile(seg, 10) > 0.8:   # 滑音/转音
        slid += 1
        continue
    cent = (m - round(m)) * 100
    devs.append(cent)
devs = np.array(devs)
print(f"滑音/转音音符(跳过): {slid}")
if len(devs):
    print(f"【音准】(稳定音符 {len(devs)} 个)")
    print(f"  绝对偏差中位数: {np.median(np.abs(devs)):.1f} 音分")
    print(f"  平均绝对偏差: {np.mean(np.abs(devs)):.1f} 音分")
    print(f"  四分位距(IQR): {np.percentile(np.abs(devs),75)-np.percentile(np.abs(devs),25):.1f} 音分")
    print(f"  ±25 音分内: {(np.abs(devs)<25).mean()*100:.1f}%")
    print(f"  ±50 音分内: {(np.abs(devs)<50).mean()*100:.1f}%")
    print(f"  平均偏高/偏低(系统性): {np.mean(devs):+.1f} 音分")

# ---- 颤音 (长音上的音高调制谱) ----
print(f"\n【颤音】(长音 >=0.45s)")
rates, depths = [], []
for a, b, m, d in notes:
    if d < 0.45:
        continue
    idx = (tv >= a) & (tv <= b)
    seg = midi[idx] * 100
    if len(seg) < 30:
        continue
    x = seg - np.linspace(seg[0], seg[-1], len(seg))     # 去线性漂移
    x = x - x.mean()
    w = np.hanning(len(x))
    sp = np.abs(np.fft.rfft(x * w))
    fr = np.fft.rfftfreq(len(x), d=(tv[1]-tv[0]))
    band = (fr >= 3) & (fr <= 9)
    if band.sum() and sp[band].max() > 0:
        rates.append(fr[band][np.argmax(sp[band])])
        depths.append(2 * np.sqrt(2) * np.std(x))        # 近似峰峰值/2
if rates:
    print(f"  有效长音: {len(rates)}")
    print(f"  颤音速率中位数: {np.median(rates):.1f} Hz (理想 4~7)")
    print(f"  颤音深度中位数: {np.median(depths):.0f} 音分 (理想 30~100)")
else:
    print("  未测到稳定颤音 (可能几乎不用颤音)")

# ---- 音域 ----
print(f"\n【音域】")
lo, hi = np.percentile(f0v, 5), np.percentile(f0v, 95)
print(f"  常用音域: {12*np.log2(lo/440)+69:.0f} ~ {12*np.log2(hi/440)+69:.0f} MIDI = {12*np.log2(hi/lo):.1f} 半音")
print(f"  极端: {f0v.min():.0f}~{f0v.max():.0f} Hz")

# ---- 长音气息 ----
drift, amp_drop = [], []
for a, b, m, d in notes:
    if d < 0.5:
        continue
    idx = (tv >= a) & (tv <= b)
    seg = midi[idx]
    k = max(len(seg)//3, 1)
    drift.append((np.mean(seg[-k:]) - np.mean(seg[:k])) * 100)
if drift:
    print(f"\n【气息】长音({len(drift)}个) 首尾音高漂移中位数: {np.median(drift):+.0f} 音分")

# ---- 节奏: 与伴奏拍点对齐 ----
print(f"\n【节奏】")
onset_env_i = librosa.onset.onset_strength(y=yi, sr=sr)
tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env_i, sr=sr, start_bpm=75, units="time")
tempo = float(np.atleast_1d(tempo)[0])
onsets = librosa.onset.onset_detect(y=yv, sr=sr, units="time")
if len(beats) > 4:
    per = np.median(np.diff(beats))
    offs = []
    for o in onsets:
        k = np.argmin(np.abs(beats - o))
        offs.append((o - beats[k]) / per)
    offs = np.array(offs)
    print(f"  伴奏 BPM: {tempo:.1f} | 拍长 {per*1000:.0f} ms | 检测拍数 {len(beats)}")
    print(f"  人声起音偏移: 中位 {np.median(np.abs(offs))*per*1000:.0f} ms | 均值 {np.mean(np.abs(offs))*per*1000:.0f} ms")
    print(f"  系统倾向(正=偏晚): {np.median(offs)*per*1000:+.0f} ms")
    print(f"  落在 ±1/4 拍内: {(np.abs(offs)<0.25).mean()*100:.1f}%")
