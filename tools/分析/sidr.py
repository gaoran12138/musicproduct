#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分离质量自评：SI-SDR 重建一致性 + 泄漏/能量/频带分析

用法（走 .venv-as）：
    python sidr.py <mix> <vocals> <accomp>
    python sidr.py <mix> <vocals> <accomp> --ref-vocals a.wav --ref-accomp b.wav
    python sidr.py ... --json out.json

说明：
  * 不给 --ref 时只能算"自洽性"：vocals+accomp 与 mix 的吻合度、两轨串音。
    这能查出分离器输出损坏、电平放错、丢帧等问题，但**不能**代替主观听感。
  * 给了参考分轨（如人工精修/另一套模型）才是真正的 SI-SDR 质量分。
"""
import argparse
import json
import sys

import numpy as np

try:
    import librosa
except Exception as e:  # pragma: no cover
    print(f"[!!] 需要 librosa: {e}", file=sys.stderr)
    sys.exit(2)

SR = 44100


def load_mono(path, sr=SR):
    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y.astype(np.float64)


def load_stereo(path, sr=SR):
    y, _ = librosa.load(str(path), sr=sr, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y])
    return y.astype(np.float64)


def align(*arrs):
    n = min(a.shape[-1] for a in arrs)
    return [a[..., :n] for a in arrs]


def si_sdr(est, ref):
    """经典 SI-SDR（返回 dB 与最佳缩放系数 α）。"""
    ref = ref - ref.mean()
    est = est - est.mean()
    est, ref = align(est, ref)
    denom = np.dot(ref.ravel(), ref.ravel()) + 1e-12
    alpha = float(np.dot(est.ravel(), ref.ravel()) / denom)
    target = alpha * ref
    noise = est - target
    return 10.0 * np.log10((np.sum(target ** 2) + 1e-12) / (np.sum(noise ** 2) + 1e-12)), alpha


def rms_db(x):
    r = float(np.sqrt(np.mean(x ** 2)))
    return 20.0 * np.log10(r + 1e-12), r


def band_energy(x, lo, hi, sr=SR):
    spec = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    m = (freqs >= lo) & (freqs < hi)
    return float(np.sum(spec[m] ** 2))


def corr(a, b):
    a, b = align(a, b)
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt(np.sum(a ** 2) * np.sum(b ** 2)) + 1e-12
    return float(np.sum(a * b) / d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mix", help="原始混音（或母带）")
    ap.add_argument("vocals", help="分离出的人声")
    ap.add_argument("accomp", help="分离出的伴奏")
    ap.add_argument("--ref-vocals", dest="ref_vocals", help="参考人声（可选，用于真 SI-SDR）")
    ap.add_argument("--ref-accomp", dest="ref_accomp", help="参考伴奏（可选）")
    ap.add_argument("--json", dest="json_out", help="把结果写入 json")
    args = ap.parse_args()

    mix = load_stereo(args.mix)
    voc = load_stereo(args.vocals)
    acc = load_stereo(args.accomp)
    mix, voc, acc = align(mix, voc, acc)
    total = voc + acc

    rec_db, alpha = si_sdr(total, mix)
    mix_db, mix_r = rms_db(mix)
    voc_db, voc_r = rms_db(voc)
    acc_db, acc_r = rms_db(acc)
    tot_db, tot_r = rms_db(total)
    # 残差按最优缩放对齐后计算：只反映波形差异，不含整体增益差
    residual_db, _ = rms_db(mix - alpha * total)
    leak = corr(voc, acc)

    e_voc = voc_r ** 2
    e_acc = acc_r ** 2
    voc_share = 100.0 * e_voc / (e_voc + e_acc + 1e-12)

    # 人声频带（200-4000Hz）里，伴奏占了多少 -> 伴奏里残留人声的粗略指标
    vb_voc = band_energy(voc, 200, 4000)
    vb_acc = band_energy(acc, 200, 4000)
    vb_mix = band_energy(mix, 200, 4000)
    acc_vocal_band_share = 100.0 * vb_acc / (vb_acc + vb_voc + 1e-12)

    out = {
        "mix": args.mix,
        "vocals": args.vocals,
        "accompaniment": args.accomp,
        "duration_s": round(mix.shape[-1] / SR, 3),
        "reconstruction": {
            "si_sdr_db": round(rec_db, 2),
            "scale_alpha": round(alpha, 4),
            "residual_dbfs": round(residual_db, 2),
        },
        "levels_dbfs": {"mix": round(mix_db, 2), "vocals": round(voc_db, 2),
                        "accompaniment": round(acc_db, 2), "sum": round(tot_db, 2),
                        "sum_minus_mix": round(tot_db - mix_db, 2)},
        "leakage": {
            "corr_vocals_accomp": round(leak, 4),
            "vocals_energy_share_pct": round(voc_share, 2),
            "accomp_vocal_band_share_pct": round(acc_vocal_band_share, 2),
        },
    }

    if args.ref_vocals and args.ref_accomp:
        rv = load_stereo(args.ref_vocals)
        ra = load_stereo(args.ref_accomp)
        rv, ra = align(rv, ra)
        v_db, v_alpha = si_sdr(voc, rv)
        a_db, a_alpha = si_sdr(acc, ra)
        out["reference"] = {
            "vocals_si_sdr_db": round(v_db, 2),
            "vocals_scale": round(v_alpha, 4),
            "accomp_si_sdr_db": round(a_db, 2),
            "accomp_scale": round(a_alpha, 4),
        }

    print("=" * 66)
    print("  分离质量自评")
    print("=" * 66)
    print(f"  时长 {out['duration_s']}s | 混音 {mix_db:.2f} dBFS")
    print()
    print("【重建一致性】vocals + accompaniment vs mix")
    print(f"  SI-SDR      {rec_db:+.2f} dB     （>10 好，<5 有问题）")
    print(f"  缩放 α      {alpha:.4f}          （≈1.0 说明电平对，偏离=增益放错）")
    print(f"  残差电平    {residual_db:.2f} dBFS（应 ≈ -60 以下）")
    print(f"  两轨和电平  {tot_db:.2f} vs 混音 {mix_db:.2f} dBFS（差 {tot_db - mix_db:+.2f}）")
    print()
    print("【电平】")
    print(f"  人声        {voc_db:+.2f} dBFS   伴奏 {acc_db:+.2f} dBFS")
    print(f"  人声能量占比 {voc_share:.1f}%")
    print()
    print("【串音 / 泄漏】")
    print(f"  两轨相关系数          {leak:+.4f}（|r|<0.1 干净，>0.3 明显串音）")
    print(f"  伴奏中 200-4000Hz 占比 {acc_vocal_band_share:.1f}%（偏高=人声没抠干净）")

    verdict = []
    if rec_db > 10:
        verdict.append("[OK] 重建一致性良好")
    elif rec_db > 5:
        verdict.append("[..] 重建一致性一般，检查是否有丢帧/重采样")
    else:
        verdict.append("[!!] 重建一致性差：分轨和凭空少了内容，可能漏轨或电平错")
    if abs(alpha - 1.0) > 0.15:
        verdict.append(f"[..] 缩放 α={alpha:.3f}，分离器对输出做了整体归一化（不影响听感，合成时按 α 对齐）")
    if abs(leak) > 0.3:
        verdict.append("[!!] 两轨高度相关：分离基本没起作用（或输入是单轨复制）")
    if residual_db > -20:
        verdict.append("[..] 对齐后残差仍偏大：可能源文件与分轨不是同一版/有重采样")

    if "reference" in out:
        r = out["reference"]
        print()
        print("【参考对比】真正的 SI-SDR")
        print(f"  人声 {r['vocals_si_sdr_db']:+.2f} dB | 伴奏 {r['accomp_si_sdr_db']:+.2f} dB")
        print(f"  （分轨模型常见 6-15dB，Roformer 类偏高；<3dB 说明这一轨基本没分开）")

    print()
    for v in verdict:
        print("  " + v)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n  json -> {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
