# -*- coding: utf-8 -*-
"""判断 Wui229 是否属于 R&B: 反拍强调 / 摇摆感 / 和弦扩展音"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

FULL = r"D:\musicProduct\素材\Wui229-陳嫺靜.mp3"
ACC = r"D:\musicProduct\分轨\Wui229_伴奏\Wui229_伴奏.wav"
VOX = r"D:\musicProduct\分轨\Wui229_伴奏\Wui229_人声.wav"

y, sr = librosa.load(FULL, sr=22050, mono=True)
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, start_bpm=78, units="frames")
tempo = float(np.atleast_1d(tempo)[0])
beat_times = librosa.frames_to_time(beats, sr=sr)
print(f"BPM: {round(tempo,1)} | 检测到拍点: {len(beat_times)}")

# 1) 反拍强调: 比较 1/3 拍 vs 2/4 拍 的起音强度
strength = onset_env
if len(beat_times) > 8:
    idx = librosa.time_to_frames(beat_times, sr=sr)
    idx = idx[idx < len(strength)]
    vals = strength[idx]
    on13 = vals[0::2].mean()   # 假设第1拍起为 1
    on24 = vals[1::2].mean()
    print(f"起音强度 1&3拍: {on13:.2f} | 2&4拍: {on24:.2f} | 2&4更强: {on24 > on13}")

# 2) 摇摆感: 拍内起始点相位分布 (0=正拍, 0.5=直八分, 0.67=摇摆八分)
if len(beat_times) > 4:
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time")
    phases = []
    for o in onsets:
        i = np.searchsorted(beat_times, o)
        if 0 < i < len(beat_times):
            span = beat_times[i] - beat_times[i - 1]
            if span > 0.2:
                phases.append((o - beat_times[i - 1]) / span)
    phases = np.array(phases)
    if len(phases):
        off = phases[(phases > 0.2) & (phases < 0.9)]
        print(f"拍内副拍相位中位数: {np.median(off):.3f}  (0.50=直拍, 0.60-0.70=摇摆/Shuffle)")
        print(f"副拍相位分布 25/50/75%: {np.percentile(off,25):.2f} / {np.percentile(off,50):.2f} / {np.percentile(off,75):.2f}")

# 3) 和弦扩展音: 用伴奏做色度分析, 看 7/9 音占比
ya, sra = librosa.load(ACC, sr=22050, mono=True)
chroma = librosa.feature.chroma_cqt(y=ya, sr=sra)
prof = chroma.mean(axis=1)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
top = sorted(zip(names, prof), key=lambda x: -x[1])[:7]
print("色度前7:", ", ".join(f"{n}:{v:.2f}" for n, v in top))

# 判断是否存在 7 度音(与主音相距10或11半音)常驻
root = top[0][0]
ri = names.index(root)
p7 = prof[(ri + 10) % 12]
maj7 = prof[(ri + 11) % 12]
third = prof[(ri + 4) % 12]
m3 = prof[(ri + 3) % 12]
ninth = prof[(ri + 2) % 12]
print(f"假设主音 {root}: 大三度 {third:.2f} | 小三度 {m3:.2f} | 小七度 {p7:.2f} | 大七度 {maj7:.2f} | 九度(二度) {ninth:.2f}")

# 4) 人声 (旋律装饰/连音倾向)
yv, srv = librosa.load(VOX, sr=22050, mono=True)
f0, voiced, _ = librosa.pyin(yv, fmin=80, fmax=800, sr=srv)
f0v = f0[~np.isnan(f0)]
if len(f0v) > 100:
    semis = 12 * np.log2(f0v / np.median(f0v))
    print(f"人声音高波动(半音标准差): {np.std(semis):.2f} | 音域跨度(5-95%): {np.percentile(semis,95)-np.percentile(semis,5):.1f} 半音")
