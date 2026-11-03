# Rhythm Hold v4.1 · PC Integrated

micro:bit V2 + GE1354 GamePad 负责菜单、方向键输入、判定和双 OLED；电脑通过 USB 串口发送曲目和谱面，并在电脑音频设备上播放音乐。每首歌使用一个 `chart.json`。

以下命令都在仓库根目录运行。

## 安装与启动

1. 准备 Python 3.10+，创建并激活虚拟环境。
2. 安装 Python 依赖：`python -m pip install -r projects/pc-integrated/requirements.txt`。
3. 安装 FFmpeg 并确保 `ffmpeg -version` 可运行。首次播放或音频更新时会生成 `songs/<id>/cache.wav`。
4. 按 [songs/README.md](songs/README.md) 放置音频文件。GitHub 仓库不包含音频和缓存。
5. 在 [micro:bit Python 编辑器](https://python.microbit.org/) 中打开本目录的 `microbit_main.py` 并刷入设备。
6. 关闭浏览器串口监视器，连接 GamePad 后启动电脑主机：

```sh
python projects/pc-integrated/pc_player.py --port COM3
```

Windows 用设备管理器确认 COM 端口；macOS/Linux 可用 `python -m serial.tools.list_ports` 查看。电脑与浏览器不能同时占用同一个串口。音乐由电脑播放，请确认电脑音频输出。

## 设备操作

- 摇杆上/下选择歌曲；右推加载谱面，在 READY 页面再次右推开始。
- 方向键跟随箭头演奏。
- 游戏中左推暂停，右推恢复，下推退出。
- 如需对齐音频与箭头，可加 `--offset-ms 100`；正数使音频延后，单位毫秒。

## 编辑谱面

推荐使用通用 Chart Studio v1.3：

```sh
python -m pip install -r tools/chart-studio/requirements.txt
python tools/chart-studio/chart_studio.py
```

打开本版 `songs/<id>/chart.json`，导入对应音频试听后保存。也保留了随 v4.1 发布的 `chart_editor.py`，可用 `python projects/pc-integrated/chart_editor.py` 启动。两种编辑器均需要 Python 的 Tkinter；音频试听需要 pygame 和 FFmpeg。

`README.txt`、`VERSION.txt` 保留原始版本记录，其中的短命令以本目录为工作目录。
