# -*- coding: utf-8 -*-
"""鼓轨分析: 底鼓/军鼓落点 -> 反拍(backbeat) 与 16分切分度"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

files = glob.glob(r"D:\musicProduct\分轨\Wui229_分轨\*(Drums)*.wav") or glob.glob(r"D:\musicProduct\分轨\Wui229_分轨\*rums*.wav")
print("鼓轨文件:", files)
path = files[0]

y, sr = librosa.load(path, sr=22050, mono=True)
# 底鼓: 低频段; 军鼓: 中高频段
S = np.abs(librosa.stft(y))
freqs = librosa.fft_frequencies(sr=sr)
low = S[(freqs >= 40) & (freqs <= 120)].mean(axis=0)
mid = S[(freqs >= 1500) & (freqs <= 5000)].mean(axis=0)

def env(x, hop=512):
    return librosa.util.normalize(librosa.onset.onset_strength(S=np.abs(librosa.stft(np.zeros(1))), sr=sr)) if False else x

low_env = librosa.onset.onset_strength(S=np.abs(librosa.stft(y, n_fft=2048)), sr=sr, freq=None)
# 直接对频段做起音包络
def band_onset(y, sr, fmin, fmax):
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
    band = S[(fr >= fmin) & (fr <= fmax)].mean(axis=0)
    # 半波整流差分作为起音强度
    d = np.diff(band, prepend=band[0])
    return np.clip(d, 0, None)

kick = band_onset(y, sr, 40, 120)
snare = band_onset(y, sr, 1500, 5000)

# 拍点 (用全曲估计的 78.3 BPM)
tempo = 78.3
period = 60.0 / tempo
hop = 512
n = len(kick)
t = librosa.frames_to_time(np.arange(n), sr=sr, hop_length=hop)

# 找相位偏移: 使底鼓起音总和最大
best_phase, best_score = 0.0, -1
for ph in np.arange(0, period, period / 96):
    idx = np.round((t - ph) / period).astype(int)
    m = (idx >= 0) & (idx < 1000)
    ref = np.zeros(2000)
    np.add.at(ref, idx[m], 1)
    beats_t = ph + np.arange(2000) * period
    ki = np.clip(np.searchsorted(t, beats_t), 0, n - 1)
    score = kick[ki].sum()
    if score > best_score:
        best_score, best_phase = score, ph

beat_times = best_phase + np.arange(int((t[-1] - best_phase) / period) + 1) * period
beat_times = beat_times[beat_times < t[-1]]
print(f"BPM {tempo} | 对齐相位 {best_phase:.3f}s | 拍数 {len(beat_times)}")

def strength_at(env, times):
    idx = np.clip(np.searchsorted(t, times), 0, len(env) - 1)
    return env[idx]

k_b = strength_at(kick, beat_times)
s_b = strength_at(snare, beat_times)

def split(v):
    return v[0::2], v[1::2]

k13, k24 = split(k_b)
s13, s24 = split(s_b)
print(f"底鼓  1&3拍: {k13.mean():.4f} | 2&4拍: {k24.mean():.4f}")
print(f"军鼓  1&3拍: {s13.mean():.4f} | 2&4拍: {s24.mean():.4f}")
if s24.mean() > s13.mean():
    print("-> 军鼓强在 2&4 = 标准 backbeat ✓ (R&B/流行特征)")
else:
    print("-> 军鼓强在 1&3 = 非典型 backbeat")

# 16 分切分度: 起音在拍内的 16 分格分布
onset_times = librosa.onset.onset_detect(onset_envelope=librosa.onset.onset_strength(y=y, sr=sr), sr=sr, units="time")
pos16 = []
for o in onset_times:
    i = np.searchsorted(beat_times, o)
    if 0 < i < len(beat_times):
        span = beat_times[i] - beat_times[i - 1]
        if span > 0.2:
            pos16.append(((o - beat_times[i - 1]) / span) * 4)  # 0-4 的 16 分格
pos16 = np.array(pos16)
hist, _ = np.histogram(pos16, bins=16, range=(0, 4))
hist = hist / max(hist.sum(), 1)
print("拍内 16 分格分布 (每格=1/16 拍):")
print("  " + " ".join(f"{v*100:4.1f}%" for v in hist))
offbeat = hist[[1, 3, 5, 7, 9, 11, 13, 15]].sum()
print(f"落在 16 分副格的比例: {offbeat*100:.1f}%  (>40% = 切分感强, R&B/funk 常见)")
