# 标准流程 SOP：弹唱/卡拉OK 字幕视频制作

> 本机已验证的完整流程（晴天案例）。**以后做类似任务（某首歌的分轨/歌词/和弦/右手/字幕）一律照此执行。**

## 一、目标产出物（一套 6 类文件）

| 文件 | 内容 |
|---|---|
| `歌曲名_歌词.srt` / `.lrc` | 歌词（带时间轴） |
| `歌曲名_歌词+和弦.srt` | 和弦行 + 歌词行（GP4 精确版） |
| `歌曲名_歌词+和弦_标准版.srt` | 简化和弦名版（无 GP4 时用） |
| `歌曲名_歌词+和弦+右手.srt` | 三行：和弦 / 右手 / 歌词（最全） |
| `歌曲名_字幕A_歌词.srt` / `_字幕B_和弦右手.srt` | 双字幕轨拆分（PR 上下摆放） |
| `仅供参考.srt` | 全程"仅供参考"水印 |

## 二、本机环境（已就绪，路径固定）

| 组件 | 位置/命令 |
|---|---|
| Python 3.10（主环境） | `D:\musicProduct\tools\python310\python.exe` |
| audio-separator（UVR 分离，主工具） | `D:\musicProduct\.venv-as\Scripts\audio-separator.exe` |
| ffmpeg / ffprobe | `D:\musicProduct\tools\ffmpeg\bin\` |
| UVR 模型缓存 | `D:\tmp\audio-separator-models\`（BS-Roformer / MelBand Karaoke / htdemucs_6s） |
| PyGuitarPro（GP 解析） | 主环境已装 |
| librosa（BPM 实测） | `.venv-as` 内（随 audio-separator 安装） |
| 歌词 API | lrclib.net（无需登录） |

> 注：spleeter 仅在早期验证环节使用过，**最终标准流程不再使用**。

运行前固定环境变量：`PATH` 加 `tools\ffmpeg\bin`；`PYTHONIOENCODING=utf-8`；临时目录指向 `tools\tmp`。

## 三、标准流程（10 步）

1. **收集输入**：音频文件（mp3/flac）、可选 GP4/GP5 谱、可选现成 LRC
2. **（可选）音频分离** → `.venv-as\Scripts\audio-separator.exe` + 模型：
   - 干净人声/伴奏：`model_bs_roformer_ep_317_sdr_12.9755.ckpt`（BS-Roformer-Viperx-1297）
   - 去主唱（和声保留）：`mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt`
   - 多分轨（鼓/贝斯/吉他/钢琴等）：`htdemucs_6s.yaml`
   - 和声轨 = karaoke 伴奏 − 纯伴奏（`make_backup_vocals.py`）
3. **获取歌词**：`tools\字幕\make_lrc_srt.py` → 自动从 lrclib.net 取 LRC 并转 SRT（UTF-8-sig）
4. **测 BPM**：用分离的鼓轨（或原曲）跑 librosa：`beat_track(start_bpm=75)` → 取慢速值（防倍速误判）；再用"总时长/小节数"交叉验证
5. **提取和弦**
   - **有 GP4**（最准）：`tools\字幕\gp4_to_srt.py` → 从吉他轨音符逐小节反推和弦，时间轴按音频总时长缩放对齐
   - **无 GP4**：`tools\字幕\make_chord_srt.py` → 和弦挂在歌词行上（标准名：主歌 Em7 Cadd9 G D/F#、副歌 G→Em C→D B7→Em C→D）
6. **右手标识**（仅 GP4）：`tools\字幕\rh_srt.py` → 分解琶音（弦序）或扫弦方向（↓正拍/↑反拍，节奏点位来自谱面）
7. **拆分双轨**：`tools\字幕\split_subs.py` → 生成 `字幕A_歌词` + `字幕B_和弦右手`（供其他软件；PR 内用三行合并版）
8. **水印**：复制 `仅供参考.srt` 模板，改文字/时长即可（PR 里建议用基本图形文字层，不占字幕轨）
9. **PR 使用**：见 `PR歌词字幕教程.md`（单字幕轨三行合并显示，PR 一次只能有一条活动字幕轨）
10. **质检清单**（见下）

## 四、脚本索引（`D:\musicProduct\tools\`）

| 脚本 | 用途 |
|---|---|
| `make_lrc_srt.py` | 拉取歌词 → LRC + SRT |
| `make_chord_srt.py` | 无 GP：歌词行对齐的和弦 SRT（标准名） |
| `gp4_to_srt.py` | 有 GP：逐小节和弦 SRT（GP4 精确） |
| `rh_srt.py` | 右手标识（分解/扫弦）+ 三行组合版 |
| `split_subs.py` | 拆分为 歌词 / 和弦右手 两条字幕 |
| `make_backup_vocals.py` | 和声轨 = karaoke伴奏 − 纯伴奏 |
| `download.py` | 带断点续传+校验的下载器（网络不稳必用） |

## 五、质量检查清单（每次必查）

- [ ] 每句歌词都有和弦（脚本断言通过）
- [ ] 第一句歌词时间点 ≈ 人声实际出现时间（对齐检查）
- [ ] BPM 与结构吻合（前奏小节数 × 每小节秒数 ≈ 前奏时长）
- [ ] GP4 版：和弦名符合谱面音符（抽查转位/加音合理）
- [ ] SRT 全部 UTF-8 编码
- [ ] PR 导出时字幕选"烧录"

## 六、常见坑（踩过的）

1. **沙箱/管道**：本会话受限环境里，子进程输出接管道会被拒；全权限模式下无此问题
2. **GPU 并行**：两个 TF 任务并行必 OOM/内存爆 → 一律串行
3. **网络不稳**：大文件下载一律用 `download.py`（断点续传+完整性校验），国内用阿里云 PyPI 镜像 `-i https://mirrors.aliyun.com/pypi/simple/`
4. **numpy 冲突**：spleeter(TF2.9) 要 numpy<2；audio-separator 要 numpy≥2 → **必须分环境**（主环境 / `.venv-as`）
5. **编码**：控制台输出一律 `PYTHONIOENCODING=utf-8`；SRT 写 UTF-8-sig
6. **GP4 无和弦名**：GP4 格式不带和弦名，需从音符反推（GP5+ 才有 chord 数据）
7. **中文路径/文件名**：Windows + 中文文件名没问题，但控制台日志会因 cp1252 崩 → 见坑 5

## 七、视频渲染默认设置（省 token 约定）

- **静默渲染**：ffmpeg 一律加 `-loglevel error -stats_period 60`，不拉进度日志（日志是最贵的 token 开销）
- 默认样式：模糊封面背景 + 居中清晰封面 + 底部歌词（微软雅黑白字黑边），**1080p + 帧率 15**（静态图 30fps 浪费），NVENC 硬编码 CQ22，AAC 320k
- 字幕烧录用 **ASS**（`srt2ass.py` 转换），避免命令行转义问题；filter 用 `-filter_complex_script` 写文件，绕开 cmd/PowerShell 引号坑
- 渲染命令不要写 .bat（LF 换行会被 cmd 误解），直接用 pwsh 调 ffmpeg
- 封面优先用同名文件（`歌名.webp` 等），没有则提取内嵌封面，都没有才用脚本生成背景图
