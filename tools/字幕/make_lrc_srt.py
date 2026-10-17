import urllib.request, json, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

# 1) 搜索
s = json.loads(fetch("https://lrclib.net/api/search?track_name=%E6%99%B4%E5%A4%A9&artist_name=%E5%91%A8%E6%9D%B0%E4%BC%A6"))
best = None
for r in s:
    if r.get("syncedLyrics"):
        # prefer the one closest to our 269s track
        dur = r.get("duration") or 0
        if best is None or abs(dur - 270) < abs((best.get("duration") or 0) - 270):
            best = r
print("picked:", best.get("trackName"), "|", best.get("albumName"), "| duration", best.get("duration"))
lrc = best["syncedLyrics"]
open(r"D:\musicProduct\字幕\晴天_歌词.lrc", "w", encoding="utf-8").write(lrc)
print("LRC lines:", len(lrc.splitlines()))

# 2) LRC -> SRT
def ts2sec(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + float(s)

def fmt_srt(sec):
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms2 = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms2:03d}"

# parse LRC lines into (time, text) pairs; also extract metadata tags [ti:][ar:] to ignore
entries = []
for line in lrc.splitlines():
    times = re.findall(r"\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]", line)
    text = re.sub(r"\[.*?\]", "", line).strip()
    if not times:
        continue
    for m, s in times:
        sec = int(m) * 60 + float(s)
        entries.append((sec, text))
entries.sort()

srt = []
for i, (t, text) in enumerate(entries):
    end = entries[i + 1][0] if i + 1 < len(entries) else t + 4.0
    srt.append(f"{i+1}\n{fmt_srt(t)} --> {fmt_srt(end)}\n{text}\n")

open(r"D:\musicProduct\字幕\晴天_歌词.srt", "w", encoding="utf-8-sig").write("\n".join(srt))
print("SRT entries:", len(srt))
print("first:", srt[0].strip())
print("last:", srt[-1].strip())
