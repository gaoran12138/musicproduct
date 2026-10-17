# -*- coding: utf-8 -*-
"""音准问题地图: 列出偏差最大的音符 + 分析偏差规律"""
import sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import numpy as np
import librosa

path = glob.glob(r"D:\musicProduct\分轨\分裂翻唱_分轨\*(Vocals)*.wav")[0]
y, sr = librosa.load(path, sr=22050, mono=True)
hop = 256
f0, flag, prob = librosa.pyin(y, fmin=70, fmax=800, sr=sr, frame_length=2048, hop_length=hop)
t = librosa.times_like(f0, sr=sr, hop_length=hop)
ok = (~np.isnan(f0)) & flag & (prob > 0.6)
midi = np.full(len(f0), np.nan); midi[ok] = 69+12*np.log2(f0[ok]/440.0)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
nm = lambda m: f"{names[int(round(m))%12]}{int(round(m))//12-1}"

notes = []
i = 0
while i < len(midi):
    if np.isnan(midi[i]):
        i += 1; continue
    j = i
    while j+1 < len(midi) and not np.isnan(midi[j+1]) and abs(midi[j+1]-midi[i]) < 0.6 and (t[j+1]-t[i]) < 3.0:
        j += 1
    d = t[j]-t[i]
    if d >= 0.15:
        seg = midi[i:j+1]
        sd = float(np.std(seg))
        if sd <= 60:                      # 排除滑音
            m = float(np.median(seg))
            notes.append((t[i], d, m, (m-round(m))*100))
    i = j+1

devs = np.array([n[3] for n in notes])
print(f"稳定音符 {len(notes)} 个")
print(f"偏差: 中位 {np.median(np.abs(devs)):.1f} | 平均 {np.mean(np.abs(devs)):.1f} | 标准差 {np.std(devs):.1f} 音分")
print(f"偏高({devs>0}) {100*(devs>0).mean():.0f}% | 偏低 {100*(devs<0).mean():.0f}%")
print(f">25音分(明显) {(np.abs(devs)>25).mean()*100:.0f}% | >40音分(严重) {(np.abs(devs)>40).mean()*100:.0f}% | >50: {(np.abs(devs)>50).mean()*100:.0f}%")

print(f"\n=== 偏差最大的 15 个位置 (可以去听这些时间点) ===")
print(f"{'时间':>8s} {'音名':>5s} {'时长':>5s} {'偏差':>7s} {'方向':>4s}")
for a, d, m, dv in sorted(notes, key=lambda x: -abs(x[3]))[:15]:
    print(f"{a:7.1f}s {nm(m):>5s} {d:4.2f}s {dv:+6.0f}音分 {'偏高' if dv>0 else '偏低'}")

print(f"\n=== 按音区看 ===")
for lab, lo, hi in (("低 <C4", 0, 60), ("中 C4~D#4", 60, 64), ("换声 E4~G4", 64, 68), ("高 >=G#4", 68, 100)):
    sel = np.array([(lo <= n[2] < hi) for n in notes])
    if sel.sum() >= 3:
        dd = np.abs(devs[sel])
        print(f"  {lab:12s} {sel.sum():3d}个 中位 {np.median(dd):5.1f}音分 | >25音分 {100*(dd>25).mean():4.0f}%")

print(f"\n=== 按音长看 (短音容易急/偏高) ===")
for lab, sel in (("长音 >=0.5s", np.array([n[1] >= 0.5 for n in notes])), ("短音 <0.5s", np.array([n[1] < 0.5 for n in notes]))):
    if sel.sum() >= 3:
        dd = np.abs(devs[sel])
        print(f"  {lab:12s} {sel.sum():3d}个 中位 {np.median(dd):5.1f}音分 | 均值Signed {np.mean(devs[sel]):+5.1f}")

print(f"\n=== 按乐句位置 (句子开头 vs 结尾) ===")
# 用相邻音符间隔 >0.4s 视为乐句边界
starts, ends = [], []
prev_end = -10
for k, (a, d, m, dv) in enumerate(notes):
    if a - prev_end > 0.4:
        starts.append(abs(dv))
    prev_end = a + d
for k, (a, d, m, dv) in enumerate(notes):
    nxt = notes[k+1][0] if k+1 < len(notes) else 1e9
    if nxt - (a+d) > 0.4:
        ends.append(abs(dv))
if len(starts) >= 3:
    print(f"  乐句首音 {len(starts)}个 中位 {np.median(starts):5.1f}音分")
if len(ends) >= 3:
    print(f"  乐句末音 {len(ends)}个 中位 {np.median(ends):5.1f}音分")
