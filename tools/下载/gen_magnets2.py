# -*- coding: utf-8 -*-
"""磁力链接每行一个，不带标签"""
from urllib.parse import quote

infohash = {
    1: "7KSMXDRS7NW2EUX6SGPUXTR7XXVQL66B",
    2: "3QN3AH62RK2D23A5KOPLRAMFTHK33AMA",
    3: "WSABG5TIH6G5IRKMOCWIFHP43QFV4W4F",
    4: "DZLVJ6FETSOIIWKOV6HGSJ6GBOMIWMPU",
    5: "ZVK2LA6OTLXEATMY5P73EZTFZJSG4HHW",
    6: "QPBWFVSOT4DDUOCCQNB6UAO2WRFL4Y4T",
    7: "GZ37MOVXUTLEJNO33V6SLL6OSRZSHT3F",
    8: "J4V3BTR257Y4LOO5V2CIQHGJKVVXW5S4",
}
TR = [
    "http://104.143.10.186:8000/announce",
    "udp://104.143.10.186:8000/announce",
    "http://tracker.openbittorrent.com:80/announce",
    "http://tracker3.itzmx.com:6961/announce",
    "udp://tracker1.itzmx.com:8080/announce",
    "udp://tracker2.itzmx.com:6961/announce",
    "http://nyaa.tracker.wf:7777/announce",
    "https://tracker.ghostchu-services.top/announce",
    "https://tracker.anibt.net/announce",
    "https://tr.bangumi.moe:9696/announce",
]

lines = []
for ep in sorted(infohash):
    dn = f"[ANi] 穹廬下的魔女 - {ep:02d} [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]"
    m = f"magnet:?xt=urn:btih:{infohash[ep]}&dn={quote(dn)}"
    for tr in TR:
        m += f"&tr={quote(tr, safe='')}"
    lines.append(m)

with open(r"D:\musicProduct\文档\穹庐下的魔女_01-08_磁力链接.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("行数:", len(lines))
