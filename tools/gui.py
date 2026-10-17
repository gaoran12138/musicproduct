#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本地 Web GUI（只监听 127.0.0.1）：把 music.py 的子命令包成按钮

用法：
    python tools\\gui.py [--port 8765]
或：music gui --port 8765

设计：
    * 单任务：同一时间只跑一个命令，避免 8GB 显存 OOM
    * 子进程输出实时进内存缓冲，前端轮询 /status 拉取
    * 只允许白名单子命令，不接受任意 shell
"""
import argparse
import json
import os
import queue
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / "tools" / "python310" / "python.exe"
MUSIC = ROOT / "music.py"
AUDIO_EXT = {".wav", ".flac", ".mp3", ".m4a"}
ALLOW = {"doctor", "separate", "uvr", "lyrics", "chords", "report", "analyze",
         "render", "pack", "meta", "sidr", "batch", "publish", "log", "trend", "info", "freeze"}

STATE = {"proc": None, "argv": [], "lines": [], "rc": None, "lock": threading.Lock()}


def list_media():
    out = []
    for base in ("素材", "分轨", "成品", "字幕"):
        d = ROOT / base
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in AUDIO_EXT | {".srt", ".mp4"}:
                out.append(str(p.relative_to(ROOT)))
                if len(out) >= 400:
                    return out
    return out


def env():
    e = dict(os.environ)
    e["PATH"] = os.pathsep.join([str(ROOT / "tools" / "ffmpeg" / "bin"),
                                 str(ROOT / "tools" / "cuda" / "bin"), e.get("PATH", "")])
    e["MODEL_PATH"] = str(ROOT / "pretrained_models")
    e["FFMPEG_BIN"] = str(ROOT / "tools" / "ffmpeg" / "bin")
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    e["HF_ENDPOINT"] = "https://hf-mirror.com"
    return e


def start(argv):
    if not argv or argv[0] not in ALLOW:
        return False, f"不允许的子命令：{argv[:1]}"
    with STATE["lock"]:
        if STATE["proc"] is not None and STATE["proc"].poll() is None:
            return False, "上一个任务还在跑，等它结束"
        STATE["lines"] = ["$ music " + " ".join(argv)]
        STATE["rc"] = None
        STATE["argv"] = argv
        proc = subprocess.Popen([str(PY), str(MUSIC)] + argv, cwd=str(ROOT), env=env(),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", bufsize=1)
        STATE["proc"] = proc

    def pump():
        assert proc.stdout is not None
        for ln in proc.stdout:
            with STATE["lock"]:
                STATE["lines"].append(ln.rstrip("\n"))
                if len(STATE["lines"]) > 4000:
                    del STATE["lines"][:1000]
        code = proc.wait()
        with STATE["lock"]:
            STATE["rc"] = code
            STATE["lines"].append(f"[exit {code}]")

    threading.Thread(target=pump, daemon=True).start()
    return True, "started"


PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>musicProduct 控制台</title>
<style>
:root{--bg:#f7f4ee;--card:#fff;--ink:#2b2925;--mut:#7d766c;--line:#e2dbcf;--acc:#3d5a80;--ok:#4a7c59;--bad:#b34a32}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Microsoft YaHei",system-ui,sans-serif}
header{padding:22px 28px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:14px}
h1{font-size:19px;margin:0;letter-spacing:.5px}header span{color:var(--mut);font-size:13px}
main{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:20px 28px 40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.card h2{font-size:14px;margin:0 0 12px;color:var(--acc);letter-spacing:.6px;text-transform:uppercase}
label{display:block;font-size:12px;color:var(--mut);margin:8px 0 4px}
input,select,textarea{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;font:inherit;background:#fdfcf9}
button{margin-top:12px;padding:8px 16px;border:0;border-radius:6px;background:var(--acc);color:#fff;font:inherit;cursor:pointer}
button.ghost{background:#eceae4;color:var(--ink)}
button:disabled{opacity:.45;cursor:default}
#out{grid-column:1/-1}.log{background:#1f1d1a;color:#e8e2d6;border-radius:8px;padding:14px;height:340px;overflow:auto;
font:12.5px/1.55 Consolas,monospace;white-space:pre-wrap}
.rc{font-size:12px;color:var(--mut);margin-top:8px}
.bar{display:flex;gap:8px;flex-wrap:wrap}
</style></head><body>
<header><h1>musicProduct 控制台</h1><span>本地 · 127.0.0.1 · 串行执行</span></header>
<main>
<section class="card"><h2>1 分离</h2>
  <label>音频文件</label><input id="sep_file" list="files" placeholder="素材\\某某 - 歌名.flac">
  <label>模型</label><select id="sep_parts"><option>2stems</option><option>4stems</option><option>5stems</option></select>
  <label>只处理前 N 秒（0 = 整首）</label><input id="sep_dur" type="number" value="0" min="0">
  <button onclick="runSep()">spleeter 分离</button>
  <div class="bar" style="margin-top:10px">
    <input id="uvr_file" list="files" placeholder="UVR：音频文件">
    <select id="uvr_model"><option value="bs">BS-Roformer 最干净</option><option value="karaoke">Karaoke 去主唱</option><option value="demucs6">demucs6 六轨</option></select>
    <button class="ghost" onclick="runUvr()">UVR</button>
  </div>
</section>

<section class="card"><h2>2 字幕 / 视频</h2>
  <label>音频</label><input id="ly_file" list="files" placeholder="素材\\某某 - 歌名.flac">
  <button onclick="run(['lyrics',val('ly_file')])">抓歌词（lrclib）</button>
  <button class="ghost" onclick="run(['chords',val('ly_file')])">识别和弦</button>
  <label style="margin-top:14px">渲染：音频 + SRT</label>
  <input id="rd_audio" list="files" placeholder="音频">
  <input id="rd_srt" list="files" placeholder="字幕 .srt" style="margin-top:6px">
  <input id="rd_cover" list="files" placeholder="封面图（可空）" style="margin-top:6px">
  <button onclick="runRender()">渲染 mp4</button>
</section>

<section class="card"><h2>3 分析</h2>
  <label>录音 / 人声轨</label><input id="an_file" list="files" placeholder="分轨\\...（Vocals）...flac">
  <button onclick="run(['report',val('an_file')])">音准报告 PNG</button>
  <button class="ghost" onclick="run(['analyze',val('an_file')])">完整声学分析</button>
  <button class="ghost" onclick="run(['log',val('an_file')])">记入训练档案</button>
  <div class="bar" style="margin-top:10px"><button class="ghost" onclick="run(['trend'])">训练趋势</button></div>
</section>

<section class="card"><h2>4 维护</h2>
  <button onclick="run(['doctor'])">环境自检 doctor</button>
  <button class="ghost" onclick="run(['pack'])">分轨 wav→flac 预览</button>
  <button class="ghost" onclick="run(['pack','--apply'])">真转 flac</button>
  <button class="ghost" onclick="run(['meta'])">刷新项目元数据</button>
  <button class="ghost" onclick="run(['info'])">路径配置</button>
  <label>批量：目录</label><input id="bt_dir" placeholder="素材\\某专辑目录">
  <button class="ghost" onclick="run(['batch',val('bt_dir'),'--parts',val('sep_parts')])">批量分离</button>
</section>

<section class="card" id="out"><h2>输出</h2>
  <div class="log" id="log">等待任务…</div>
  <div class="rc" id="rc"></div>
</section>
</main>
<datalist id="files"></datalist>
<script>
const val=id=>document.getElementById(id).value.trim();
const LOG=document.getElementById('log'), RC=document.getElementById('rc');
let timer=null;
async function loadFiles(){const r=await fetch('/files');const j=await r.json();
  document.getElementById('files').innerHTML=j.files.map(f=>`<option value="${f}">`).join('');}
async function run(argv){argv=argv.filter(x=>x&&x.length);
  const r=await fetch('/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({argv})});
  const j=await r.json(); if(!j.ok){LOG.textContent=j.msg;return;}
  LOG.textContent=''; poll();}
function poll(){clearInterval(timer);timer=setInterval(async()=>{
  const r=await fetch('/status');const j=await r.json();
  LOG.textContent=j.lines.join('\\n'); LOG.scrollTop=LOG.scrollHeight;
  if(j.running){RC.textContent='运行中…';}else{RC.textContent='已结束，退出码 '+j.rc;clearInterval(timer);}
},700);}
function runSep(){const d=parseFloat(val('sep_dur')||'0');
  const a=['separate',val('sep_file'),'--parts',val('sep_parts')]; if(d>0)a.push('-d',String(d)); run(a);}
function runUvr(){run(['uvr',val('uvr_file'),'-m',val('uvr_model')]);}
function runRender(){const a=['render',val('rd_audio'),'--srt',val('rd_srt')];
  if(val('rd_cover'))a.push('--cover',val('rd_cover')); run(a);}
loadFiles();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self._send(200, PAGE)
        elif self.path == "/files":
            self._send(200, json.dumps({"files": list_media()}), "application/json")
        elif self.path == "/status":
            with STATE["lock"]:
                proc = STATE["proc"]
                running = bool(proc and proc.poll() is None)
                body = {"running": running, "rc": STATE["rc"],
                        "argv": STATE["argv"], "lines": STATE["lines"][-400:]}
            self._send(200, json.dumps(body), "application/json")
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path != "/run":
            self._send(404, "not found")
            return
        try:
            n = int(self.headers.get("content-length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
            argv = [str(x) for x in payload.get("argv", [])]
        except Exception as e:
            self._send(200, json.dumps({"ok": False, "msg": f"bad request: {e}"}), "application/json")
            return
        okk, msg = start(argv)
        self._send(200, json.dumps({"ok": okk, "msg": msg}), "application/json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if not PY.exists():
        print(f"[!!] 找不到解释器 {PY}", file=sys.stderr)
        return 2
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), H)
    print(f"  GUI -> http://127.0.0.1:{args.port}  (Ctrl+C 退出)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
