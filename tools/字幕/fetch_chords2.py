import urllib.request, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

urls = [
    "http://www.tan8.com/guitarChords-106087.html",
    "http://www.tan8.com/guitarChords-96647.html",
    "https://keynes.tw/song27.htm",
]

for u in urls:
    print("=" * 20, u)
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=30).read()
        for enc in ("utf-8", "gb18030", "big5"):
            try:
                t = html.decode(enc)
                break
            except Exception:
                continue
        t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
        t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
        t = re.sub(r"<[^>]+>", " ", t)
        t = re.sub(r"\s+", " ", t)
        # find chorus area
        for kw in ["颳風", "刮风", "颳風這天", "副歌"]:
            i = t.find(kw)
            if i >= 0:
                print(f"--- {kw}: {t[max(0,i-30):i+400]}")
                break
        else:
            chords = re.findall(r"[A-G][#b]?(?:m|maj|dim|sus|add\d+)?\d*(?:/[A-G][#b]?)?", t)
            print("no keyword; chord tokens:", chords[:40])
    except Exception as e:
        print("FAIL", type(e).__name__, e)
