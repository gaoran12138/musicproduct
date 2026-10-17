# -*- coding: utf-8 -*-
"""从 dmhy RSS 找 内封(软字幕) 版本磁力"""
import urllib.request, re, sys, time, urllib.parse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def fetch(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
        except Exception as e:
            print("retry", i + 1, type(e).__name__)
            time.sleep(3)
    raise RuntimeError("failed")

kw = urllib.parse.quote("穹廬下的魔女")
t = fetch(f"http://share.dmhy.org/topics/rss?keyword={kw}")
items = re.findall(r"<item>.*?</item>", t, re.S)
print("items:", len(items))

softsub = []
for it in items:
    tm = re.search(r"<title>\s*<!\[CDATA\[(.*?)\]\]>\s*</title>", it, re.S)
    mg = re.search(r'<enclosure url="(magnet:[^"]+)"', it)
    if not tm or not mg:
        continue
    title = tm.group(1).strip()
    if "内封" in title:
        m = re.search(r"\[0?(\d+)\]", title) or re.search(r"-\s*0?(\d+)\s*\[", title)
        epn = m.group(1) if m else "?"
        softsub.append((epn, title, mg.group(1)))

softsub.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 99)
for epn, title, mag in softsub:
    print(f"[EP{epn}] {title[:95]}")
print("内封版本数:", len(softsub))

# 输出 LoliHouse 1-8 磁力 (每行一个, 写文件)
loli = {e: m for e, t, m in softsub if "LoliHouse" in t}
lines = []
for ep in sorted(loli, key=int):
    lines.append(loli[ep])
with open(r"D:\musicProduct\文档\穹庐下的魔女_内封版_01-08_磁力.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nLoliHouse 内封版 集数:", sorted(loli, key=int))
print("已写入: D:\\musicProduct\\穹庐下的魔女_内封版_01-08_磁力.txt")
