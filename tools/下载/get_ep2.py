# -*- coding: utf-8 -*-
"""提取 第2集 LoliHouse 内封版磁力"""
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
for it in items:
    tm = re.search(r"<title>\s*<!\[CDATA\[(.*?)\]\]>\s*</title>", it, re.S)
    mg = re.search(r'<enclosure url="(magnet:[^"]+)"', it)
    if not tm or not mg:
        continue
    title = tm.group(1).strip()
    if "LoliHouse" in title and re.search(r"-\s*0?2\s*\[", title):
        print(title)
        print(mg.group(1))
        break
