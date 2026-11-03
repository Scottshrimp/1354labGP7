# Rhythm Hold · Standalone Gentle Mode

micro:bit V2 + GE1354 GamePad 独立运行版，源自 Rhythm Hold v4.1。设备内嵌单音主旋律与 114 个简单单键提示，刷入后可用电池运行，无需电脑播放音频或发送谱面。

本页命令从仓库根目录运行；本目录的 `docs/` 和 `AGENTS.md` 中使用的短路径以本项目目录为根。

## 刷入和操作

在 [micro:bit Python 编辑器](https://python.microbit.org/) 打开 `projects/standalone/src/deploy/main.py` 并刷入 micro:bit V2。只需这一个文件，不需要上传 MIDI 或 JSON。

- 摇杆右推开始；方向键跟随箭头。
- 左推暂停，右推恢复；暂停时下推退出；结果页左推返回。
- 操作后让摇杆回中，再进行下一次操作。
- P12 输出音乐，P0/P1 留给摇杆；实际接线和玩法见 [usage.txt](docs/usage.txt)。

## 编辑和构建

构建和测试使用 Python 3.10+ 标准库。只有桌面试听需要 pygame；GUI 需要 Python 提供 Tkinter。压缩音频导入另需 FFmpeg，MIDI 试听不需要 FFmpeg。

```sh
python -m pip install -r projects/standalone/requirements-editor.txt
python projects/standalone/src/chart_studio.py
```

打开 `projects/standalone/music/megalovania/chart.json`；使用 Import Audio 选择同目录 `source.mid` 试听主旋律。保存后构建，再重新刷入生成文件：

```sh
python projects/standalone/src/tools/build_song.py
python -m unittest discover -s projects/standalone/src/tests -v
```

普通构建保留编辑后的谱面；加 `--make-chart` 会覆盖为默认简单谱面。单键间隔至少 1000 ms，不允许同时输入。`src/microbit_main.py` 中的歌曲数据和 `src/deploy/main.py` 都由构建器生成，请勿手工修改生成部分。

提交生成文件时以 Python 3.13 为基准。其他受支持版本仍可构建，但标准库 `ast.unparse` 可能生成不同的括号格式；构建器会检查生成代码的 AST 与源码一致。

歌曲源文件为用户提供的 MIDI；转换器当前固定读取第 3 轨（从 0 开始编号），并非任意 MIDI 的通用导入器。素材来源和再分发权限见仓库 [发布说明](../../docs/publishing.md)。

桌面逻辑模拟不能代替硬件验证，发布前应检查 P12 声音、方向键、摇杆、双 OLED、振动和暂停同步。更多编辑器说明见 [chart_studio.md](docs/chart_studio.md)。
