# -*- coding: utf-8 -*-
"""Wui229 拼色图 v8: 10 块, 尺寸悬殊 (最大/最小面积差 5 倍+), 粗黑线分隔"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

W, H = 1920, 1080

CREAM  = (242, 232, 213)
RED    = (179, 74, 50)
BLUE   = (61, 90, 128)
YELLOW = (217, 169, 59)
TERRA  = (198, 124, 96)
BLACK  = (26, 26, 26)

# ==== 10 块: 由不规则的多次切割产生, 尺寸差异明显 ====
# (x0, y0, x1, y1, color)
blocks = [
    (0,    0,    380,  520,  BLUE),     # 窄高块 (小)
    (380,  0,    1180, 300,  YELLOW),   # 上中宽块
    (380,  300,  1180, 520,  RED),      # 中中块
    (0,    520,  560,  940,  TERRA),    # 左下大块
    (0,    940,  560,  1080, YELLOW),   # 左下细条 (最小)
    (560,  520,  1180, 760,  BLUE),     # 中下块
    (560,  760,  1360, 1080, CREAM),    # 底部中间 (唯一留白 + 歌词区, 800宽居中)
    (1180, 0,    1920, 200,  YELLOW),   # 右上细条 (小)
    (1180, 200,  1920, 760,  RED),      # 右侧最大块
    (1360, 760,  1920, 1080, BLUE),     # 右下块
]

img = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(img)

for x0, y0, x1, y1, color in blocks:
    d.rectangle([x0, y0, x1, y1], fill=color)

# 粗黑线 (每块描边 -> 块间即为粗黑线)
LW = 22
for x0, y0, x1, y1, _ in blocks:
    d.rectangle([x0, y0, x1, y1], outline=BLACK, width=LW)

areas = sorted((x1 - x0) * (y1 - y0) for x0, y0, x1, y1, _ in blocks)
print("块数:", len(blocks), "| 最小面积:", areas[0], "| 最大面积:", areas[-1],
      "| 倍数:", round(areas[-1] / areas[0], 1))

# 颗粒做旧
rng = np.random.default_rng(7)
noise = rng.normal(0, 6.0, (H, W, 1)).astype(np.float32)
img = Image.fromarray(np.clip(np.asarray(img).astype(np.float32) + noise, 0, 255).astype(np.uint8))

# 暗角
vig = Image.new("L", (W, H), 0)
ImageDraw.Draw(vig).ellipse([-W * 0.3, -H * 0.3, W * 1.3, H * 1.3], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(200))
img = Image.composite(img, Image.new("RGB", (W, H), (30, 26, 32)), vig)

img.save(r"D:\musicProduct\素材\图片\bg_wui229.png")
print("v8 saved")
