# -*- coding: utf-8 -*-
"""无封面歌曲的默认背景图: 深色渐变 + 歌名/歌手"""
from PIL import Image, ImageDraw, ImageFont
import math, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

W, H = 1920, 1080
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img)

# 垂直渐变 (深蓝紫 -> 深黑)
top = (36, 26, 66)
bot = (10, 10, 16)
for y in range(H):
    t = y / (H - 1)
    r = int(top[0] + (bot[0] - top[0]) * t)
    g = int(top[1] + (bot[1] - top[1]) * t)
    b = int(top[2] + (bot[2] - top[2]) * t)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# 细装饰线 (居中上下)
line_color = (120, 100, 160)
d.line([(W // 2 - 260, 640), (W // 2 + 260, 640)], fill=line_color, width=2)

def font(size, path=r"C:\Windows\Fonts\msyh.ttc"):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# 标题: 吉他手
f_title = font(180)
f_sub = font(56)
t1 = "吉他手"
t2 = "陈绮贞"

bbox = d.textbbox((0, 0), t1, font=f_title)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
d.text(((W - tw) / 2 - bbox[0], 300 - bbox[1]), t1, font=f_title, fill=(235, 230, 245))

bbox2 = d.textbbox((0, 0), t2, font=f_sub)
tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
d.text(((W - tw2) / 2 - bbox2[0], 690 - bbox2[1]), t2, font=f_sub, fill=(170, 155, 200))

img.save(r"D:\musicProduct\素材\图片\bg_jts.png")
print("background saved")
