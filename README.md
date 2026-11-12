# musicProduct

本地音乐内容工厂：**人声分离 → 歌词 → 字幕 → 视频渲染 → 演唱分析**，全部收在一个命令行入口 `music.py`。

为一个实际需求长出来的工具链：给自己做弹唱伴奏视频、给翻唱录音做声学评估。用的都是本地模型与本地 ffmpeg，不上传任何音频。

## 能做什么

| 子命令 | 作用 | 底层 |
|---|---|---|
| `separate` | 2 / 4 / 5 轨分离（人声、伴奏、鼓、贝斯、钢琴…） | spleeter 2.4 + TensorFlow GPU |
| `uvr` | 高质量分离：BS-Roformer、Karaoke（去主唱留和声）、6 轨 | audio-separator + torch cu126 |
| `lyrics` | 抓同步歌词 → `.lrc` + `.srt` | lrclib.net，失败自动回落本地识别 |
| `lyrics --asr` | 离线识别歌词（草稿） | faster-whisper |
| `chords` | 和弦识别（含转位、变调夹） | librosa chroma + 16 模板 + Viterbi |
| `ass` / `render` | SRT → ASS → 1080p 字幕视频（封面模糊背景） | ffmpeg + NVENC |
| `report` | 音准可视化报告（音高轨迹 / 音分直方图 / 分声区） | librosa pyin + PIL |
| `analyze` | 演唱声学分析（音域、音准、颤音、换声点、HNR） | librosa |
| `chords`·`sidr` | 分离质量自评（SI-SDR、泄漏、增益） | numpy |
| `log` / `trend` | 训练档案与趋势（jsonl + 走势图） | — |
| `batch` / `publish` | 批量流水线 / 一键 B 站投稿包 | — |
| `pack` / `meta` | 分轨 wav→flac 无损压缩、项目元数据 | ffmpeg |
| `doctor` | 19 项环境自检（两套解释器、GPU、模型、目录） | — |
| `gui` | 本地 Web 控制台（点按钮跑命令，实时日志） | http.server |

## 快速开始

```bat
music.bat doctor                      :: 环境自检
music.bat separate "素材\歌.flac"      :: 2 轨 -> 分轨\
music.bat uvr "素材\歌.flac" -m bs     :: BS-Roformer 高质量分离
music.bat lyrics "素材\歌.flac"        :: 歌词 -> 字幕\*.srt/.lrc
music.bat render "素材\歌.flac" --srt "字幕\歌_歌词.srt" --cover 封面.jpg
music.bat gui                         :: 网页控制台 http://127.0.0.1:8765
```

不带参数运行 `music.bat` 会打印全部子命令；`music.bat <子命令> -h` 看参数。

## 两套 Python 环境（别混用）

| 环境 | 装了什么 | 谁在用 |
|---|---|---|
| `tools\python310\` | spleeter 2.4 + tensorflow-gpu 2.9.3 + numpy 1.23 | `separate`、老脚本 |
| `.venv-as\` | torch 2.13+cu126 + audio-separator + librosa + faster-whisper + numpy 2.x | `uvr`、`analyze`、`report`、`chords`、`sidr`、`lyrics --asr` |

分开的原因很实在：spleeter 钉死 `tensorflow<2.10`（numpy<2），audio-separator 要 `numpy>=2`，同环境装不下。

依赖已锁定：`tools/requirements-main.txt`、`tools/requirements-as.txt`。

## 仓库里有什么、没有什么

**有**：`music.py` 与全部工具脚本（`tools/`）、文档、字幕样例、和弦谱、封面图。

**没有**（都在 `.gitignore` 里）：运行环境本身（`tools/python310`、`tools/ffmpeg`、`tools/cuda`、`.venv-as`）、预训练模型（`pretrained_models/`，400MB+）、任何音频与视频素材、分离产物、发布包。

所以 clone 下来要自己搭环境：Python 3.10 + ffmpeg（含 ffprobe）+ CUDA 11.3/cuDNN 8.1（spleeter）与 CUDA 12.6（torch），步骤见 [`文档/SPLEETER_使用说明.md`](文档/SPLEETER_使用说明.md) 与 [`工作区说明.md`](工作区说明.md)。

## 目录

```
music.py            入口（子命令分发、环境拼装）
music.bat           Windows 启动器
tools/分离 字幕 分析 下载 图片   各脚本
字幕/ 成品/ 分轨/ 素材/ 档案/    产物与素材（多为本地目录）
文档/               使用说明、SOP、PR 教程
docs/agents/        agent skills 配置（issue tracker / triage / domain docs）
```

## 已知限制

- 分离必须**串行**：8GB 显存跑不动两个并行任务。
- 和弦识别是**辅助**：模板匹配 + Viterbi 平滑，实测《晴天》137 段、平均置信度 0.84，仍会有强力和弦/转位误判，需要人工校最后几个。
- 歌词识别是**草稿**：中文唱段错字明显，适合没有歌词来源时兜底。
- 训练分析假设素材是**清唱**：带伴奏的录音要先分离再用。

## 免责声明

本项目只含代码与工具链，不含任何音频素材。`字幕/` 下含少量第三方歌曲的歌词与和弦标注，仅用于本机练习与研究，版权归原作者所有，请勿再分发。仓库不附带许可证（暂未指定）。
