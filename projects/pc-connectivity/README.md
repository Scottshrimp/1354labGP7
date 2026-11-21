# Rhythm Hold 双人电脑联机（开发测试版）

两台 micro:bit V2 + GE1354 GamePad 通过 USB 连接本机，网页控制选曲和开始；电脑播放单机版 MEGALOVANIA 的 MIDI 主旋律，设备负责判定，网页显示成绩。也可先用一台调试。此版本尚未完成实机验收。

## 启动

1. 用 Chrome 打开 [micro:bit Python Editor](https://python.microbit.org/)，将 `src/main.py` 导入干净项目，分别刷入两台 micro:bit。刷写完成后关闭编辑器串口，再连接 GamePad。回单机模式时重新刷入 standalone 程序；网页内刷写尚未实现。
2. 在 macOS/Linux 上，先运行 `python3 -m venv "$HOME/.local/share/rhythm-hold-pc-venv"`，再运行 `"$HOME/.local/share/rhythm-hold-pc-venv/bin/python" -m pip install -r projects/pc-connectivity/requirements.txt`。虚拟环境放在项目外，避免项目路径含冒号时 Python 拒绝创建环境。本机已创建该环境。
3. 运行 `"$HOME/.local/share/rhythm-hold-pc-venv/bin/python" projects/pc-connectivity/src/server.py`。Windows 可在不含冒号的项目路径内创建 `.venv`，并使用 `.venv\Scripts\python.exe`。首次启动会在 `.cache/` 生成 MIDI 主旋律 WAV，可能需要一些时间。
4. 用本机浏览器打开终端显示的 `http://127.0.0.1:8765`。选择歌曲并点击“下载谱面”；所有参加设备显示准备完成后点击“开始”。如音乐与箭头有固定偏差，可调整音频偏移：正数使音乐延后，负数使音乐提前，单位毫秒。播放过程中可点击“结束”，成绩按分数、最佳连击排序。

每台设备的串口一次只能由一个程序占用。若设备未连接，检查 USB 数据线、Python Editor 是否仍占用串口及网页错误。关闭服务使用 Ctrl+C。两台电脑接口不足时可使用供电可靠的 USB 集线器。

## 数据与限制

初始曲目引用 `projects/standalone/music/megalovania/` 的现有 MIDI 和谱面；不自动生成谱面。电脑 WAV 使用 standalone 预览工具的单声部旋律，不是商业录音。`songs.json` 是曲库目录列表（路径相对本目录），新增歌曲目录需要 `song.json`、`chart.json` 和符合现有 MIDI 工具假设的 MIDI：当前转换器固定取第 3 轨。不同格式的歌曲需要扩展转换器。音乐素材的来源与授权见仓库发布说明。

设备接收完整谱面到内存，4 字节一音符，另有一字节判定状态；当前歌曲 114 音符占用 456 字节谱面数据。传输带长度与 Fletcher-16 校验和、逐帧确认及重发。网页上的 100%/准备完成指设备已检查整份谱面，不等于永久存储；断电和刷写后需重新下载。上限 2000 音符是软件限制，实际内存容量尚未测量。

PC 和设备通过多次往返采样估计设备时钟，再约定未来时间开始；准确度取决于串口、设备循环和电脑音频延迟。分数与连击由设备计算：Perfect 100、Good 50，Miss 归零连击。沿用单机版判定反馈：Perfect 绿灯、Good 黄灯、Miss 红灯并短暂振动；5×5 灯阵显示倒计时和连击个位数。断线中止整局，结果保留已收到的数据。

**尚需实机验证：**新增打击灯光、振动和倒计时；刷入和运行时内存、两个 OLED 和方向键、两台设备并行传输与断线、同步误差、音画延迟及连续重玩。项目以往记录中外接左方向键存在待查问题。桌面模拟不能替代以上验证，也不保证特定同步精度。

## 验证

```sh
python3 -m unittest discover -s projects/pc-connectivity/tests -v
```
