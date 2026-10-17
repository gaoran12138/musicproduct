import soundfile as sf
import numpy as np
import os

base = r"D:\musicProduct\分轨\晴天_分轨v2"

karaoke_inst = os.path.join(base, "karaoke", "周杰倫,周杰伦 - 晴天_(Instrumental)_mel_band_roformer_karaoke_aufr33_viperx_sdr_10.wav")
bs_inst = os.path.join(base, "bsroformer", "周杰倫,周杰伦 - 晴天_(Instrumental)_model_bs_roformer_ep_317_sdr_12.wav")

a, sr_a = sf.read(karaoke_inst, dtype="float32")
b, sr_b = sf.read(bs_inst, dtype="float32")
print("karaoke_inst:", a.shape, sr_a)
print("bs_inst     :", b.shape, sr_b)
assert sr_a == sr_b
n = min(len(a), len(b))
backup = a[:n] - b[:n]

os.makedirs(os.path.join(base, "backup"), exist_ok=True)
out = os.path.join(base, "backup", "和声.wav")
sf.write(out, backup, sr_a, subtype="PCM_16")
print("written:", out)
print("backup peak:", float(np.max(np.abs(backup))))

# also derive: 纯伴奏-only check of RMS for info
print("rms backup:", float(np.sqrt(np.mean(backup**2))))
