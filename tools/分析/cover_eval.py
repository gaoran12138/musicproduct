# -*- coding: utf-8 -*-
"""翻唱水平量化评估: 音准 / 颤音 / 音域 / 气息 / 与伴奏的和声契合度 / 节奏稳定性"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

VOX = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0]
INST = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Instrumental)*.wav")[0]
print("人声:", VOX.split("\\")[-1])
print("伴奏:", INST.split("\\")[-1])

yv, sr = librosa.load(VOX, sr=22050, mono=True)
yi, _ = librosa.load(INST, sr=22050, mono=True)
dur = len(yv) / sr
print(f"时长: {dur:.1f}s")

# ---------- 1) 音高轨迹 ----------
f0, vflag, vprob = librosa.pyin(yv, fmin=70, fmax=900, sr=sr, frame_length=2048)
times = librosa.times_like(f0, sr=sr)
mask = ~np.isnan(f0)
f0v = f0[mask]
tv = times[mask]
print(f"有声帧: {mask.sum()} ({mask.mean()*100:.1f}%)")

# 滑音/颤音/气息等短时波动
cents = 1200 * np.log2(f0v / 440.0)

# ---------- 2) 音准: 半音网格偏差 ----------
# 以全局中位音为基准, 计算半音余数 (相对最近的十二平均律音)
semi = 12 * np.log2(f0v / 440.0)
dev = (semi - np.round(semi)) * 100   # 音分
# 只统计"稳定段"(短时变化小的地方), 排除滑音
d1 = np.gradient(semi)
stable = np.abs(d1) < 0.06              # 每帧半音变化 < 0.06 => 稳定音
dev_stable = dev[stable]
print(f"\n【音准】")
print(f"  稳定段占比: {stable.mean()*100:.1f}%")
print(f"  偏差中位数: {np.median(np.abs(dev_stable)):.1f} 音分")
print(f"  偏差均值: {np.mean(np.abs(dev_stable)):.1f} 音分 | 90分位: {np.percentile(np.abs(dev_stable),90):.1f} 音分")
print(f"  落在 ±25 音分内(可接受): {(np.abs(dev_stable)<25).mean()*100:.1f}%")
print(f"  落在 ±50 音分内(明显可辨): {(np.abs(dev_stable)<50).mean()*100:.1f}%")

# ---------- 3) 颤音 ----------
# 稳定段内音高的周期性调制
if stable.sum() > 200:
    seg = cents[stable]
    seg = seg - np.convolve(seg, np.ones(31) / 31, mode="same")
    # 用自相关估计调制频率
    ac = np.correlate(seg, seg, mode="full")[len(seg) - 1:]
    ac = ac / (ac[0] + 1e-9)
    hop_t = (times[1] - times[0])
    lo, hi = int(0.05 / hop_t), int(0.20 / hop_t)   # 5-20 Hz
    if hi < len(ac):
        pk = lo + int(np.argmax(ac[lo:hi]))
        rate = 1.0 / (pk * hop_t)
        print(f"\n【颤音】")
        print(f"  调制速率: {rate:.1f} Hz (人声理想 4~7Hz)")
        print(f"  调制深度(RMS): {np.sqrt(np.mean(seg**2)):.1f} 音分")

# ---------- 4) 音域 ----------
lo_p, hi_p = np.percentile(f0v, 5), np.percentile(f0v, 95)
print(f"\n【音域】")
print(f"  5%~95%: {lo_p:.0f}~{hi_p:.0f} Hz = {12*np.log2(hi_p/lo_p):.1f} 半音")
print(f"  极值: {f0v.min():.0f}~{f0v.max():.0f} Hz")

# ---------- 5) 气息/动态 ----------
rms = librosa.feature.rms(y=yv)[0]
rms_db = 20 * np.log10(rms + 1e-9)
print(f"\n【动态】")
print(f"  动态范围(5-95分位): {np.percentile(rms_db,95)-np.percentile(rms_db,5):.1f} dB")
print(f"  平均值: {rms_db.mean():.1f} dBFS")

# 长音尾部稳定性 (气息支撑): 找连续有声 >=0.6s 的段, 看尾部音高/音量下滑
seg_id = []
i = 0
while i < len(mask):
    if mask[i]:
        j = i
        while j < len(mask) and mask[j]:
            j += 1
        if (j - i) * hop_t >= 0.6:
            seg_id.append((i, j))
        i = j
    else:
        i += 1
drops_p, drops_a = [], []
for a, b in seg_id:
    seg = f0[a:b]
    amp = rms[a:b] if b <= len(rms) else rms[a:]
    if len(seg) > 10 and len(amp) > 10:
        n1, n2 = len(seg) // 3, len(seg) // 3
        drops_p.append(12 * np.log2(np.median(seg[-n2:]) / np.median(seg[:n1])))
        drops_a.append(20 * np.log10((np.median(amp[-n2:]) + 1e-9) / (np.median(amp[:n1]) + 1e-9)))
if drops_p:
    print(f"\n【气息】(长音 {len(seg_id)} 个)")
    print(f"  长音尾部音高变化中位数: {np.median(drops_p)*100:+.0f} 音分 (>-20 为稳)")
    print(f"  长音尾部音量变化中位数: {np.median(drops_a):+.1f} dB")

# ---------- 6) 与伴奏的和声契合度 ----------
print(f"\n【与伴奏契合】")
ch_v = librosa.feature.chroma_cqt(y=yv, sr=sr)
ch_i = librosa.feature.chroma_cqt(y=yi, sr=sr)
n = min(ch_v.shape[1], ch_i.shape[1])
# 每帧: 人声主导音级 是否在伴奏色度中较强
v_pc = ch_v[:, :n].argmax(axis=0)
i_norm = ch_i[:, :n] / (ch_i[:, :n].max(axis=0, keepdims=True) + 1e-9)
in_key = i_norm[v_pc, np.arange(n)]
print(f"  人声主导音级在伴奏中的相对强度中位数: {np.median(in_key):.2f} (越接近1越契合)")

# ---------- 7) 节奏: 与伴奏拍点对齐 ----------
tempo, beats = librosa.beat.beat_track(y=yi, sr=sr, start_bpm=90, units="time")
onsets = librosa.onset.onset_detect(y=yv, sr=sr, units="time")
if len(beats) > 4 and len(onsets) > 4:
    per = np.median(np.diff(beats))
    # 每个起音到最近拍点的偏差(拍为单位)
    offs = []
    for o in onsets:
        k = np.argmin(np.abs(beats - o))
        offs.append((o - beats[k]) / per)
    offs = np.array(offs)
    print(f"\n【节奏】伴奏 BPM≈{float(np.atleast_1d(tempo)[0]):.1f}")
    print(f"  起音相对拍点偏差中位数: {np.median(np.abs(offs))*100:.1f}% 拍 ({np.median(np.abs(offs))*per*1000:.0f} ms)")
    print(f"  落在 ±15% 拍内的比例: {(np.abs(offs)<0.15).mean()*100:.1f}%")
