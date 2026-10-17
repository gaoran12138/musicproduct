# -*- coding: utf-8 -*-
"""LoliHouse 内封版 1-8 集磁力 + 全量 tracker 自动附加"""
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

# 全量 tracker 列表
TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "http://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.openbittorrent.com:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "http://tracker.torrent.eu.org:451/announce",
    "udp://explodie.org:6969/announce",
    "udp://tracker.cyberia.is:6969/announce",
    "https://tracker.cyberia.is:443/announce",
    "udp://tracker.moeking.me:6969/announce",
    "https://tracker.gbitt.info:443/announce",
    "udp://tracker.zerobytes.xyz:1337/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://tracker.tiny-vps.com:6969/announce",
    "http://tracker.gbitt.info:80/announce",
    "http://open.acgtracker.com:1096/announce",
    "https://tr.bangumi.moe:9696/announce",
    "http://tr.bangumi.moe:6969/announce",
    "http://nyaa.tracker.wf:7777/announce",
    "https://tracker.ghostchu-services.top/announce",
    "https://tracker.anibt.net/announce",
    "udp://tracker.kamigami.org:2710/announce",
    "udp://tracker.pump.moe:6969/announce",
]

# 从 dmhy 拉 LoliHouse 1-8 磁力
kw = urllib.parse.quote("穹廬下的魔女")
t = fetch(f"http://share.dmhy.org/topics/rss?keyword={kw}")
items = re.findall(r"<item>.*?</item>", t, re.S)
loli = {}
for it in items:
    tm = re.search(r"<title>\s*<!\[CDATA\[(.*?)\]\]>\s*</title>", it, re.S)
    mg = re.search(r'<enclosure url="(magnet:[^"]+)"', it)
    if not tm or not mg:
        continue
    title = tm.group(1).strip()
    m = re.search(r"-\s*0?(\d+)\s*\[", title)
    if "LoliHouse" in title and m:
        loli[int(m.group(1))] = (title, mg.group(1))

# 附加全量 tracker 生成新磁力
lines = []
for ep in sorted(loli):
    title, magnet = loli[ep]
    new = magnet
    for tr in TRACKERS:
        new += f"&tr={urllib.parse.quote(tr, safe='')}"
    lines.append(new)

out = r"D:\musicProduct\文档\穹庐下的魔女_内封版_01-08_全量tracker磁力.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("LoliHouse 集数:", sorted(loli), "| tracker 数:", len(TRACKERS))
print("已写入:", out)
for l in lines:
    print(l[:150], "...")
