import urllib.request, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

urls = [
    "https://www.kanpu8.com/chords/sunny-day/",
    "https://chord4.com/tabs/11936",
    "https://www.qinhun.com/pu/45193.html",
]

for u in urls:
    print("=" * 20, u)
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=30).read()
        # try utf-8 then gbk
        for enc in ("utf-8", "gb18030"):
            try:
                t = html.decode(enc)
                break
            except Exception:
                continue
        # strip tags
        t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
        t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
        t = re.sub(r"<[^>]+>", " ", t)
        t = re.sub(r"\s+", " ", t)
        # find chord-like content
        chord_terms = re.findall(r"[A-G][#b]?(?:m|maj|dim|aug|sus|add\d*)?\d*(?:\s|/|\|)", t)
        print("chord tokens:", chord_terms[:60])
        # print sections around 主歌/副歌/前奏
        for kw in ["前奏", "主歌", "副歌", "間奏", "间奏", "结尾", "結尾"]:
            i = t.find(kw)
            if i >= 0:
                print(f"--- {kw}: {t[max(0,i-20):i+220]}")
    except Exception as e:
        print("FAIL", type(e).__name__, e)
