# AGENTS.md

本仓库是 `D:\musicProduct`，一个本地音乐内容工厂：分离 / 歌词 / 字幕 / 视频渲染 / 演唱分析，全部走一个入口 `music.py`。

## 项目速览

- **入口**：`music.bat <子命令>`（等价于 `tools\python310\python.exe music.py <子命令>`）。不带参数会打印全部子命令。
- **两套环境，别混用**：
  - `tools\python310\`：spleeter 2.4 + tensorflow-gpu 2.9.3 + numpy 1.23（`separate` / `uvr` 之外的老脚本）
  - `.venv-as\`：torch 2.13 + audio-separator + librosa + faster-whisper + numpy 2.x（`uvr` / `analyze` / `report` / `chords` / `sidr` / `lyrics --asr`）
- **目录**：`素材\` 输入 · `分轨\` 分离产物 · `成品\` 视频 · `字幕\` srt/lrc/ass · `档案\` 报告与训练记录 · `文档\` 说明 · `发布包\` B站投稿包。
- **硬约束**：分离必须串行（8G 显存）；SRT 一律 `utf-8-sig`；控制台设 `PYTHONIOENCODING=utf-8`；渲染走 `-filter_complex_script` 文件，不写 .bat。
- 细节见 `工作区说明.md`、`标准流程_弹唱字幕制作SOP.md`。

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues in `gaoran12138/musicproduct`, operated with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles map 1:1 to `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

single-context — one `GLOSSARY.md` at the repo root plus `docs/adr/` (both created lazily, not yet present). See `docs/agents/domain.md`.
