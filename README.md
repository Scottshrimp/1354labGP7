# GE1354 Rhythm Hold

基于 micro:bit V2 和 GE1354 GamePad 的节奏游戏。当前维护两个版本：PC 整合版与独立运行版。

| 版本 | 运行方式 | 音乐 | 使用说明 |
| --- | --- | --- | --- |
| PC Integrated · v4.1 | micro:bit 通过 USB 串口连接电脑；设备负责操作、判定和显示，电脑播放音频并发送谱面 | 本地音频文件，每首歌一个谱面 | [PC 版](projects/pc-integrated/README.md) |
| Standalone · Gentle Mode | 刷入一个 Python 文件，设备可脱离电脑运行 | P12 输出内嵌的单音旋律；114 个简单单键提示 | [独立运行版](projects/standalone/README.md) |

## 文件结构

```text
projects/
  pc-integrated/
    microbit_main.py        # PC 版设备程序
    pc_player.py            # 串口主机和音频播放
    chart_editor.py         # 随 v4.1 保留的编辑器
    songs/<song-id>/        # song.json、chart.json；音频只在本地保存
    requirements.txt
  standalone/
    src/microbit_main.py    # 可读设备源码，含生成的歌曲数据
    src/deploy/main.py      # 生成的单文件刷入版
    src/chart_studio.py     # 支持 MIDI 试听的谱面编辑器
    src/tools/build_song.py
    src/tests/
    music/megalovania/     # source.mid、chart.json、song.json
    docs/
tools/
  chart-studio/            # v1.3 通用音频谱面编辑器
docs/
  publishing.md            # 发布步骤、文件范围和授权检查
.github/workflows/        # 桌面测试、语法和构建一致性检查
```

原有 `Legacy/` 保持原样，根目录和 PC 包中的重复音频移入 `local-assets/`。这两个目录、音频录音、WAV 缓存、虚拟环境和 Python 缓存都已被 Git 忽略；本地文件仍然保留。

## 快速开始

从仓库根目录运行。桌面工具建议使用 Python 3.10+；设备端使用 micro:bit MicroPython，不要直接用桌面 Python 启动设备程序。

```sh
python3 -m venv .venv
```

macOS/Linux 激活：`source .venv/bin/activate`。Windows PowerShell 激活：`.venv\Scripts\Activate.ps1`。激活后使用下方的 `python` 命令。

**PC 版**：先按 [歌曲说明](projects/pc-integrated/songs/README.md) 放置自己的音频，再安装依赖、刷入 `projects/pc-integrated/microbit_main.py`，关闭浏览器串口监视器后运行：

```sh
python -m pip install -r projects/pc-integrated/requirements.txt
python projects/pc-integrated/pc_player.py --port COM3
```

把 `COM3` 换成设备实际串口；macOS 通常是 `/dev/cu.usbmodem...`，Linux 通常是 `/dev/ttyACM0`。生成音频缓存需要系统已安装 FFmpeg。

**独立运行版**：在 [micro:bit Python 编辑器](https://python.microbit.org/) 打开并刷入 `projects/standalone/src/deploy/main.py`。运行游戏不需要电脑进程，也不需要额外复制 MIDI/JSON 到设备。

**谱面编辑**：PC 版可用 `python tools/chart-studio/chart_studio.py`；独立版使用 `python projects/standalone/src/chart_studio.py`，支持通过同一个转换器试听 MIDI。编辑器依赖和操作见各自 README。

## 验证

```sh
python -m unittest discover -s projects/standalone/src/tests -v
python projects/standalone/src/tools/build_song.py
```

构建默认保留手工谱面；`--make-chart` 会覆盖为默认简单谱面。构建只需 Python 标准库。桌面测试覆盖内嵌数据、刷入文件一致性、音乐调度、暂停恢复和整局计分；实体 GamePad 的声音、OLED、输入和振动仍需上板验证。

## 发布范围与素材

仓库保留两版源码、JSON 谱面、独立版 MIDI 和生成的设备文件。PC 音频不随仓库分发，克隆后需要自行补充。

目前未指定开源许可证；发布前需确定代码许可，以及 `music/megalovania/source.mid` 和内嵌旋律的来源与再分发权限。整理文件不代表取得了第三方音乐授权。详见 [发布说明](docs/publishing.md)。
