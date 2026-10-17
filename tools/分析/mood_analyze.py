# -*- coding: utf-8 -*-
"""分析歌曲情绪特征 -> 输出配色建议依据"""
import sys, json
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

PATH = r"D:\musicProduct\素材\Wui229-陳嫺靜.mp3"
y, sr = librosa.load(PATH, sr=22050, mono=True)
dur = len(y) / sr

# 节奏
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=90)
tempo = float(np.atleast_1d(tempo)[0])

# 调性/调式 (chroma -> Krumhansl-ish 简版)
chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
maj = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
minr = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
best = None
for i in range(12):
    for mode, prof in (("major", maj), ("minor", minr)):
        r = np.corrcoef(np.roll(prof, i), chroma)[0, 1]
        if best is None or r > best[0]:
            best = (r, names[i], mode)
key, mode = best[1], best[2]

# 能量/动态/明亮度/密集度
rms = librosa.feature.rms(y=y)[0]
cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
zcr = librosa.feature.zero_crossing_rate(y)[0]
onset_env = librosa.onset.onset_detect(y=y, sr=sr, units="time")

# 近似大调/小调 (音阶能量)
third = chroma[(names.index(key) + 4) % 12]
minor3 = chroma[(names.index(key) + 3) % 12]
mode_hint = "明亮(大调倾向)" if third > minor3 else "忧郁(小调倾向)"

print(json.dumps({
    "时长秒": round(dur, 1),
    "BPM": round(tempo, 1),
    "调性": f"{key} {mode}",
    "三音倾向": mode_hint,
    "RMS均值": round(float(rms.mean()), 4),
    "动态范围(95-5分位)": round(float(np.percentile(rms, 95) - np.percentile(rms, 5)), 4),
    "谱质心(明亮度Hz)": round(float(cent.mean()), 1),
    "谱滚降Hz": round(float(rolloff.mean()), 1),
    "过零率": round(float(zcr.mean()), 4),
    "起音密度(个/秒)": round(len(onset_env) / dur, 2),
    "色度向量": [round(float(x), 2) for x in chroma],
}, ensure_ascii=False, indent=2))
