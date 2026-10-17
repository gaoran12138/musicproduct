# Spleeter 使用说明（人声/伴奏分离 · GPU 版）

Spleeter 是 Deezer 开源的音乐源分离工具，基于 TensorFlow。
本机已配置 **GPU 加速**：NVIDIA GeForce RTX 4070 Laptop（8GB 显存）。

## 一、安装位置（本次配置好的东西）

| 组件 | 位置 |
|---|---|
| 便携版 Python 3.10 | `D:\musicProduct\tools\python310\` |
| ffmpeg 7.1 + ffprobe | `D:\musicProduct\tools\ffmpeg\bin\` |
| spleeter 2.4.0 + **tensorflow-gpu 2.9.3** | 装在 python310 的 site-packages 里 |
| CUDA 11.3 运行时 + cuDNN 8.1（DLL 部署在本地，未装系统） | `D:\musicProduct\tools\cuda\bin\` |
| 预训练模型 **2stems / 4stems / 5stems**（全部已下载） | `D:\musicProduct\pretrained_models\` |
| 快捷启动脚本 | `D:\musicProduct\spleeter.bat` |
| 测试歌曲 | `D:\musicProduct\test\song.mp3` |

> 未修改系统 PATH / 注册表，不影响你现有的 Python 3.14 和 Qt 工程。
> GPU 用到的 CUDA/cuDNN 动态库放在 `tools\cuda\bin`，由 `spleeter.bat` 自动加入 PATH。

## 二、快速上手

打开 PowerShell，进入 `D:\musicProduct`，用快捷脚本运行：

```powershell
cd D:\musicProduct

# 2 轨分离：人声 + 伴奏（最常用）
.\spleeter.bat separate test\song.mp3 -o test\output -p spleeter:2stems
```

运行结束后，`test\output\song\` 里会出现：
- `vocals.wav` — 人声
- `accompaniment.wav` — 伴奏（去人声）

> 注意：spleeter 2.4.0 的 `-i` 参数已废弃，音频文件直接作为位置参数写在 `separate` 后面。

## 三、命令行用法详解

```
spleeter separate [选项] 音频文件1 [音频文件2 ...]
```

常用参数：

| 参数 | 说明 | 示例 |
|---|---|---|
| `（位置参数）` | 输入音频文件，可写多个实现批量 | `separate a.mp3 b.mp3` |
| `-o` | 输出目录（每个输入会生成一个子文件夹） | `-o D:\out` |
| `-p` | 分离模型：`spleeter:2stems` / `spleeter:4stems` / `spleeter:5stems` | `-p spleeter:5stems` |
| `-d` | 只处理前 N 秒（测试时很省时间） | `-d 30` |
| `-s` | 从第 N 秒开始处理（偏移） | `-s 60` |
| `-c` | 输出格式：wav / mp3 / ogg / m4a | `-c mp3` |
| `-b` | mp3 码率 | `-b 128k` |
| `-f` | 输出文件名模板 | `-f "{filename}/{instrument}.{codec}"` |
| `--mwf` | 使用多通道维纳滤波（效果更好，更慢） | `--mwf` |

### 三种模型对应输出（都已预下载）

| 模型 | 输出音轨 |
|---|---|
| `spleeter:2stems` | vocals（人声）、accompaniment（伴奏） |
| `spleeter:4stems` | vocals、drums（鼓）、bass（贝斯）、other（其他） |
| `spleeter:5stems` | vocals、drums、bass、piano（钢琴）、other |

### 批量处理

直接在命令后面列多个文件即可：

```powershell
.\spleeter.bat separate D:\songs\1.mp3 D:\songs\2.mp3 -o D:\out -p spleeter:2stems
```

## 四、在 Python 代码里调用

```python
# 用 D:\musicProduct\tools\python310\python.exe 运行
import os
os.environ['PATH'] = r'D:\musicProduct\tools\cuda\bin;D:\musicProduct\tools\ffmpeg\bin' + os.pathsep + os.environ['PATH']
os.environ['MODEL_PATH'] = r'D:\musicProduct\pretrained_models'

from spleeter.separator import Separator

# 加载模型（GPU 会自动使用）
separator = Separator('spleeter:2stems')

# 方式一：直接输出到文件
separator.separate_to_file('test/song.mp3', 'test/output')

# 方式二：拿到波形数据自己处理
waveform, sample_rate = separator.separate('test/song.mp3')
vocals = waveform['vocals']
accompaniment = waveform['accompaniment']
```

## 五、GPU 相关

- 已实测 TensorFlow 能识别 RTX 4070（`/device:GPU:0`，5.4GB 显存），分离任务跑在 GPU 上。
- 若想确认是否用上了 GPU，运行时可看到类似日志：
  `Created device /device:GPU:0 ... NVIDIA GeForce RTX 4070 Laptop GPU`
- 显存不足时 TensorFlow 会自动退回 CPU 计算，不影响结果，只是变慢。
- 换机器或重装后若 GPU 不识别，检查 `tools\cuda\bin` 里的 DLL 是否齐全。

## 六、常见问题

1. **找不到 ffmpeg 报错**：`spleeter.bat` 已自动把 ffmpeg 和 cuda 目录加入 PATH；
   手动调用 python 时先执行：
   ```powershell
   $env:PATH = "D:\musicProduct\tools\cuda\bin;D:\musicProduct\tools\ffmpeg\bin;$env:PATH"
   $env:MODEL_PATH = "D:\musicProduct\pretrained_models"
   ```

2. **速度**：GPU 处理远快于 CPU，一分钟音频约十几秒（取决于模型）。整首歌曲建议直接跑。

3. **模型损坏/想重下**：删掉 `D:\musicProduct\pretrained_models\<模型名>` 目录后重跑即可自动重新下载。

4. **输出音量偏小**：正常现象，分离后各音轨音量低于原曲，可用 ffmpeg 或软件再放大。

## 七、手动调用（不用快捷脚本）

```powershell
cd D:\musicProduct
$env:PATH = "D:\musicProduct\tools\cuda\bin;D:\musicProduct\tools\ffmpeg\bin;$env:PATH"
$env:MODEL_PATH = "D:\musicProduct\pretrained_models"
D:\musicProduct\tools\python310\python.exe -m spleeter separate test\song.mp3 -o test\output -p spleeter:2stems
```
