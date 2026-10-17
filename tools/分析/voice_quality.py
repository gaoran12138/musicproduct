# -*- coding: utf-8 -*-
"""嗓音条件评估: 谐噪比(HNR) / 频谱平坦度(气息声) / 频谱倾斜(明亮度) / 音色丰富度"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

files = [
    (r"D:\musicProduct\素材\转换中间\录音30.wav", "录音30 烟火(胸声区)"),
]
for path, label in files:
    y, sr = librosa.load(path, sr=22050, mono=True)
    hop = 256
    f0, flag, prob = librosa.pyin(y, fmin=70, fmax=1200, sr=sr, frame_length=2048, hop_length=hop)
    t = librosa.times_like(f0, sr=sr, hop_length=hop)
    ok = (~np.isnan(f0)) & flag & (prob > 0.55)
    midi = np.full(len(f0), np.nan); midi[ok] = 69+12*np.log2(f0[ok]/440.0)
    yc = y  # 原始

    print(f"===== {label} =====")
    # 逐帧声学指标 (只统计有声帧)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)) ** 2
    flat = librosa.feature.spectral_flatness(S=S)[0]
    cent = librosa.feature.spectral_centroid(S=np.sqrt(S), sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(S=np.sqrt(S), sr=sr)[0]
    rmsf = librosa.feature.rms(S=np.sqrt(S))[0]
    n = min(len(flat), len(f0))
    voiced = ok[:n] & (rmsf[:n] > np.percentile(rmsf[:n], 30))   # 排除弱帧

    def band(m_lo, m_hi, name):
        sel = voiced & (midi[:n] >= m_lo) & (midi[:n] < m_hi)
        if sel.sum() < 20:
            return
        f_ = flat[:n][sel]; c_ = cent[:n][sel]; ro_ = rolloff[:n][sel]
        print(f"  {name:14s} 帧数{sel.sum():5d} | 频谱平坦度 {np.median(f_):.4f} (越低越清亮/越有芯) | 质心 {np.median(c_):5.0f}Hz | 滚降 {np.median(ro_):5.0f}Hz")

    band(48, 60, "低音 C3~B3")
    band(60, 64, "中音 C4~D#4")
    band(64, 68, "换声 E4~G4")
    band(68, 76, "高音 G#4~E5")
    band(76, 96, "假声 F5+")

    # HNR (自相关法, 在稳定音符上)
    print("  --- 谐噪比 HNR (越高嗓音越干净) ---")
    idx = 0
    hnrs = []
    i = 0
    while i < len(midi):
        if np.isnan(midi[i]):
            i += 1; continue
        j = i
        while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.5:
            j += 1
        if (t[j]-t[i]) >= 0.35:
            a, b = int(t[i]*sr), int(t[j]*sr)
            seg = y[a:b]
            if len(seg) > 1024:
                seg = seg - seg.mean()
                ac = np.correlate(seg, seg, "full")[len(seg)-1:]
                ac = ac/(ac[0]+1e-12)
                lo = max(int(sr/1000), 2); hi = int(sr/70)
                if hi < len(ac):
                    r = ac[lo:hi].max()
                    if 0 < r < 1:
                        hnrs.append(10*np.log10(r/(1-r)))
            i = j
        else:
            i += 1
    if hnrs:
        print(f"  长音 {len(hnrs)} 个 | HNR 中位 {np.median(hnrs):.1f} dB  (>15 干净, 10~15 一般, <10 沙哑/漏气)")
