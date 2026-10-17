"""带重试+断点续传+完整性校验的下载脚本。
用法: python download.py <url> <dest> [timeout]
断连后自动从已下载字节数继续（Range 请求），直到完整或尝试耗尽。"""
import sys, os, time, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

url, dest = sys.argv[1], sys.argv[2]
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 120

def get_size(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.headers.get("Content-Length") or 0)
    except Exception:
        return 0

expected = get_size(url)
print(f"expected size: {expected}")

for attempt in range(1, 30):
    have = os.path.getsize(dest) if os.path.exists(dest) else 0
    if expected and have >= expected:
        print(f"OK {dest} size={have}")
        sys.exit(0)
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"}
        if have:
            headers["Range"] = f"bytes={have}-"
        print(f"attempt {attempt}: resume from {have}")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = have
            mode = "ab" if have else "wb"
            with open(dest, mode) as f:
                while True:
                    chunk = resp.read(1024 * 512)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)
        if expected and total < expected:
            raise IOError(f"incomplete: {total}/{expected}")
        print(f"OK {dest} size={total}")
        sys.exit(0)
    except Exception as e:
        print(f"attempt {attempt} failed: {type(e).__name__}: {e}")
        time.sleep(2)
print("ALL ATTEMPTS FAILED")
sys.exit(1)
