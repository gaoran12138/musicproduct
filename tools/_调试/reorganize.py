# -*- coding: utf-8 -*-
"""工作区重组：剩余文件归类 + 脚本/文档内绝对路径批量改写（保持原编码）"""
import os, sys, shutil, io

ROOT = r"D:\musicProduct"
T = os.path.join(ROOT, "tools")

def mv(src_rel, dst_rel_dir):
    src = os.path.join(ROOT, src_rel)
    if not os.path.exists(src):
        return False
    dst_dir = os.path.join(ROOT, dst_rel_dir)
    os.makedirs(dst_dir, exist_ok=True)
    shutil.move(src, os.path.join(dst_dir, os.path.basename(src)))
    return True

# ---- 1) tools 根目录剩余文件 ----
done = []
for f, d in [
    ("tools\\cover_wf.jpg", "素材\\图片"),
    ("tools\\luodayou.wav", "素材\\转换中间"),
    ("tools\\xuanshen.m4a", "素材\\转换中间"),
    ("tools\\录音31.wav", "素材\\转换中间"),
    ("tools\\录音32.wav", "素材\\转换中间"),
    ("tools\\jts_filter.txt", "tools\\_调试"),
    ("tools\\wf_filter.txt", "tools\\_调试"),
    ("tools\\wui229_filter.txt", "tools\\_调试"),
    ("tools\\render_wf.bat", "tools\\_调试"),
]:
    if mv(f, d):
        done.append(f)
aria = os.path.join(T, "aria2.zip")
if os.path.exists(aria):
    os.remove(aria); done.append("aria2.zip(zip)")
print("归类:", ", ".join(done) if done else "(无)")

# ---- 2) 路径改写表 ----
ABS = [
    ("D:\\musicProduct\\2005811843510", "D:\\musicProduct\\吉他谱"),
    ("D:\\musicProduct\\晴天_分轨v2", "D:\\musicProduct\\分轨\\晴天_分轨v2"),
    ("D:\\musicProduct\\晴天_分轨", "D:\\musicProduct\\分轨\\晴天_分轨"),
    ("D:\\musicProduct\\晴天_歌词", "D:\\musicProduct\\字幕\\晴天_歌词"),
    ("D:\\musicProduct\\晴天_和弦", "D:\\musicProduct\\字幕\\晴天_和弦"),
    ("D:\\musicProduct\\晴天_右手标识", "D:\\musicProduct\\字幕\\晴天_右手标识"),
    ("D:\\musicProduct\\晴天子幕", "D:\\musicProduct\\字幕\\晴天子幕"),
    ("D:\\musicProduct\\WeirdFishes_伴奏", "D:\\musicProduct\\分轨\\WeirdFishes_伴奏"),
    ("D:\\musicProduct\\Wui229_伴奏", "D:\\musicProduct\\分轨\\Wui229_伴奏"),
    ("D:\\musicProduct\\Wui229_分轨", "D:\\musicProduct\\分轨\\Wui229_分轨"),
    ("D:\\musicProduct\\Wui229_歌词", "D:\\musicProduct\\字幕\\Wui229_歌词"),
    ("D:\\musicProduct\\Wui229-陳嫺靜.mp3", "D:\\musicProduct\\素材\\Wui229-陳嫺靜.mp3"),
    ("D:\\musicProduct\\分裂翻唱_分轨", "D:\\musicProduct\\分轨\\分裂翻唱_分轨"),
    ("D:\\musicProduct\\原曲大人中_分轨", "D:\\musicProduct\\分轨\\原曲大人中_分轨"),
    ("D:\\musicProduct\\吉他手_伴奏", "D:\\musicProduct\\分轨\\吉他手_伴奏"),
    ("D:\\musicProduct\\周菲戈KissGoodbye_分轨", "D:\\musicProduct\\分轨\\周菲戈KissGoodbye_分轨"),
    ("D:\\musicProduct\\录音31_分轨", "D:\\musicProduct\\分轨\\录音31_分轨"),
    ("D:\\musicProduct\\录音32_分轨", "D:\\musicProduct\\分轨\\录音32_分轨"),
    ("D:\\musicProduct\\录音33_分轨", "D:\\musicProduct\\分轨\\录音33_分轨"),
    ("D:\\musicProduct\\炫神_分轨", "D:\\musicProduct\\分轨\\炫神_分轨"),
    ("D:\\musicProduct\\Radiohead_WeirdFishes_歌词", "D:\\musicProduct\\字幕\\Radiohead_WeirdFishes_歌词"),
    ("D:\\musicProduct\\陈绮贞_吉他手_歌词", "D:\\musicProduct\\字幕\\陈绮贞_吉他手_歌词"),
    ("D:\\musicProduct\\Counting_Stars_歌词", "D:\\musicProduct\\字幕\\Counting_Stars_歌词"),
    ("D:\\musicProduct\\仅供参考.srt", "D:\\musicProduct\\字幕\\仅供参考.srt"),
    ("D:\\musicProduct\\穹庐下的魔女", "D:\\musicProduct\\文档\\穹庐下的魔女"),
    ("D:\\musicProduct\\tracker列表.txt", "D:\\musicProduct\\文档\\tracker列表.txt"),
    ("D:\\musicProduct\\tools\\录音30.wav", "D:\\musicProduct\\素材\\转换中间\\录音30.wav"),
    ("D:\\musicProduct\\tools\\录音31.wav", "D:\\musicProduct\\素材\\转换中间\\录音31.wav"),
    ("D:\\musicProduct\\tools\\录音32.wav", "D:\\musicProduct\\素材\\转换中间\\录音32.wav"),
    ("D:\\musicProduct\\tools\\录音33.wav", "D:\\musicProduct\\素材\\转换中间\\录音33.wav"),
    ("D:\\musicProduct\\tools\\rec33_stereo.wav", "D:\\musicProduct\\素材\\转换中间\\rec33_stereo.wav"),
    ("D:\\musicProduct\\tools\\darenzhong.wav", "D:\\musicProduct\\素材\\转换中间\\darenzhong.wav"),
    ("D:\\musicProduct\\tools\\kissgoodbye.wav", "D:\\musicProduct\\素材\\转换中间\\kissgoodbye.wav"),
    ("D:\\musicProduct\\tools\\luodayou.wav", "D:\\musicProduct\\素材\\转换中间\\luodayou.wav"),
    ("D:\\musicProduct\\tools\\falsetto_test.wav", "D:\\musicProduct\\素材\\转换中间\\falsetto_test.wav"),
    ("D:\\musicProduct\\tools\\bg_jts.png", "D:\\musicProduct\\素材\\图片\\bg_jts.png"),
    ("D:\\musicProduct\\tools\\bg_wui229.png", "D:\\musicProduct\\素材\\图片\\bg_wui229.png"),
    ("D:\\musicProduct\\tools\\cover_wf.jpg", "D:\\musicProduct\\素材\\图片\\cover_wf.jpg"),
]

CATS = {
    "分离": ["make_backup_vocals.py"],
    "字幕": ["gp4_to_srt.py", "rh_srt.py", "split_subs.py", "make_chord_srt.py", "make_chord_srt_std.py",
             "srt2ass.py", "srt2ass_light.py", "make_lrc_srt.py", "find_softsub.py", "counting_stars_lrc.py",
             "counting_stars_merged.py", "counting_stars_concat.py", "fetch_chords.py", "fetch_chords2.py"],
    "分析": ["vocal_profile.py", "verify_notes.py", "passaggio.py", "intonation_map.py", "intonation_by_range.py",
             "intonation_by_length.py", "vibrato_by_range.py", "show_vibrato.py", "high_notes.py", "falsetto_eval.py",
             "falsetto_map.py", "rnb_check.py", "drums_analyze.py", "cover_eval.py", "cover_eval2.py",
             "voice_quality.py", "mood_analyze.py", "analyze_xuanshen.py", "analyze_xuanshen2.py",
             "yell_vs_sing.py", "compare_high.py"],
    "下载": ["download.py", "get-pip.py", "extract_cuda.py"],
    "图片": ["make_colorblock.py", "make_bg.py"],
    "_调试": ["debug_gp4.py", "debug_gp4b2.py", "inspect_gp4.py", "inspect_gp4b.py", "rhythm_gp4.py", "rhythm_gp4b.py"],
}
REL = [("tools\\%s" % s, "tools\\%s\\%s" % (cat, s)) for cat, ss in CATS.items() for s in ss]

SKIP_DIRS = (".venv-as", "python310", "cuda", "ffmpeg", "pretrained_models")

def read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc), (enc if enc != "utf-8-sig" else "utf-8-sig")
        except UnicodeDecodeError:
            continue
    return None, None

def write_text(path, text, enc):
    b = text.encode("utf-8" if enc == "utf-8-sig" else enc)
    if enc == "utf-8-sig":
        b = b"\xef\xbb\xbf" + text.encode("utf-8")
    open(path, "wb").write(b)

changed, scanned, skipped = 0, 0, 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        if not fn.lower().endswith((".py", ".md", ".bat", ".txt")):
            continue
        p = os.path.join(dirpath, fn)
        scanned += 1
        text, enc = read_text(p)
        if text is None:
            skipped += 1
            continue
        orig = text
        for a, b in ABS:
            text = text.replace(a, b)
        for a, b in REL:
            text = text.replace(a, b)
        if text != orig:
            write_text(p, text, enc)
            changed += 1

print("扫描 %d 个文件，改写 %d 个，编码未知跳过 %d 个" % (scanned, changed, skipped))
