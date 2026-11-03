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
  hardware-testing.md      # 实机验证结果和方向键待查问题
.github/workflows/        # 桌面测试、语法和构建一致性检查
```

原有 `Legacy/` 保持原样，根目录和 PC 包中的重复音频移入 `local-assets/`。这两个目录、音频录音、WAV 缓存、虚拟环境和 Python 缓存都已被 Git 忽略；本地文件仍然保留。

## 快速开始

从仓库根目录运行。桌面工具推荐 Python 3.13；设备端使用 micro:bit MicroPython，不要直接用桌面 Python 启动设备程序。

本机使用共享 Python 3.13 环境，PC 播放器依赖已安装，可直接运行下方命令。

## 手动刷入 micro:bit

1. 用 USB 数据线连接 micro:bit V2，并接好 GamePad。
2. 在 Chrome 打开 [micro:bit Python Editor](https://python.microbit.org/)。
3. 使用编辑器的打开/导入功能载入对应 Python 文件：

| 版本 | 导入文件 |
| --- | --- |
| PC Integrated | `projects/pc-integrated/microbit_main.py` |
| Standalone | `projects/standalone/src/deploy/main.py` |

4. 点击 **Send to micro:bit**，按 Chrome 提示选择并连接设备，完成刷入。
5. 启动时让摇杆回中，以便校准。

Standalone 刷入后直接在 GamePad 上运行。PC 版需要关闭编辑器的串口连接，再启动电脑播放器。

## PC 播放器

先按 [歌曲说明](projects/pc-integrated/songs/README.md) 放置自己的音频。新电脑安装依赖：

```sh
python3 -m pip install --user -r projects/pc-integrated/requirements.txt
```

Homebrew Python 若提示 `externally-managed-environment`，用户级安装可在上述命令中加 `--break-system-packages`。Windows 使用 `python` 代替 `python3`。

查看串口并启动（以下为 macOS 示例）：

```sh
python3 -m serial.tools.list_ports
python3 projects/pc-integrated/pc_player.py --port /dev/cu.usbmodem2102
```

把串口路径换成实际设备；Windows 通常为 `COM3` 等，Linux 通常为 `/dev/ttyACM0`。首次生成或更新音频缓存需要 FFmpeg；有效的现有缓存可直接使用。

## 谱面编辑

PC 版可用 `python3 tools/chart-studio/chart_studio.py`；独立版使用 `python3 projects/standalone/src/chart_studio.py`，支持 MIDI 试听。依赖和操作见各自 README。

## 验证

```sh
python -m unittest discover -s projects/standalone/src/tests -v
python projects/standalone/src/tools/build_song.py
```

构建默认保留手工谱面；`--make-chart` 会覆盖为默认简单谱面。构建只需 Python 标准库。构建后，将生成的 `projects/standalone/src/deploy/main.py` 重新导入 Chrome Python Editor 手动刷入。

桌面测试覆盖内嵌数据、刷入文件一致性、音乐调度、暂停恢复和整局计分。当前实机结果与未解决的方向键问题见 [硬件验证记录](docs/hardware-testing.md)。

## 发布范围与素材

仓库保留两版源码、JSON 谱面、独立版 MIDI 和生成的设备文件。PC 音频不随仓库分发，克隆后需要自行补充。

目前未指定开源许可证；发布前需确定代码许可，以及 `music/megalovania/source.mid` 和内嵌旋律的来源与再分发权限。整理文件不代表取得了第三方音乐授权。详见 [发布说明](docs/publishing.md)。
