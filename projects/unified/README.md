# Unified Rhythm Hold · 实机测试版

一个 micro:bit V2 程序加一个 PC host。无 host 时运行内嵌的 MEGALOVANIA；host 完成准备后，在菜单切换到 PC 曲库。PC 断线时结束当前局，约 2.5 秒后回到独立菜单。

当前为 **RAM2 分块编译测试版**。用户已确认重新刷入后正常，原先启动时的 `MemoryError` 已解决。完整 PC 音画同步和连续切换仍需实机验收；原有 `pc-integrated/` 和 `standalone/` 保留作基线。刷入使用 Chrome Python Editor。

## 此分支：歌曲时间进度灯

分支 `codex/led-song-progress` 将游戏中的 5×5 阵列用于当前歌曲进度。最上面一行从左到右填充，再向下逐行填充，直到右下角：

- 歌曲时间为 0 时全灭；每经过总时长的 1/25（4%）点亮一颗；歌曲结束时 25 颗全亮。
- 以当前歌曲的实际游戏时钟和总时长计算，独立模式用内嵌时长，PC 模式用所选歌曲的声明时长；与谱面密度、命中数和分数无关。
- 倒计时保留 3/2/1，倒计时不计入进度；暂停时灯态冻结，恢复后继续，暂停时间不计入歌曲时间。
- 游戏中不显示连击数字或暂停方框；OLED 仍显示分数和暂停菜单。结果页保留全亮，返回菜单后恢复菜单表情。

此分支从 RAM2 主线独立开发，不包含 AP/FC 灯实验。测试覆盖两种模式、不同歌曲长度、逐行像素顺序、倒计时暂停、歌曲中暂停及命中/漏按不影响进度；新灯态仍待手动刷入实测。

## 先刷入一个文件

1. 让摇杆回中，用 USB 连接 micro:bit V2 和 GamePad。
2. 在 Chrome 打开 [micro:bit Python Editor](https://python.microbit.org/)。
3. 在一个干净的编辑器项目中打开/导入 **[deploy/main.py](deploy/main.py)**，点击 **Send to micro:bit**。只需要这个文件，不需要把源码模块逐个添加到编辑器。
4. 未启动 host 时，右 OLED 应显示 `MEGALOVANIA / STANDALONE`，左 OLED 显示 `READY`。摇杆向右开始独立游戏。

`deploy/main.py` 是自动生成的单文件，约 20 KB；首行为 `# Unified RAM2`。后续大量注释是分块加载的数据，必须保留。启动器只读取自身，不会创建额外设备文件。日常修改使用 `src/microbit_main.py`，不要手改刷入文件。请使用编辑器提供的稳定 MicroPython 运行时；旧 beta 运行时曾出现摇杆 ADC 问题。

## 启动 PC host

先断开 Chrome 编辑器的串口连接，避免与 host 占用同一设备。从仓库根目录运行：

```sh
python3 projects/unified/pc_host.py
```

默认自动选择唯一的 micro:bit 串口。host 会先准备音频，再等待设备，准备完成后菜单显示 `PC SONGS`。歌曲默认复用原 PC 版曲库；本机已有两首歌的音频和缓存，新克隆需自行补齐。

手动选端口：

```sh
python3 -m serial.tools.list_ports
python3 projects/unified/pc_host.py --port /dev/cu.usbmodem2102
```

把示例端口换成实际值。新电脑安装依赖：

```sh
python3 -m pip install --user -r projects/unified/requirements.txt
```

歌曲默认复用 `../pc-integrated/songs/` 的 JSON 和本地音频。音频不在 Git 中；新克隆需要按[歌曲说明](../pc-integrated/songs/README.md)补齐。首次转换或音频更新需要 FFmpeg。`--songs /path/to/songs` 可指定其他曲库，最多 12 首。

预检歌曲而不连接设备、不打开音频输出：

```sh
python3 projects/unified/pc_host.py --check
```

若 PC 音乐与判定有固定偏差，可加 `--offset-ms 50`，正数让音乐稍晚开始，负数让音乐提前，允许范围为 -1000 到 1000 ms。初版同步仍包含串口收包延迟，实际偏移需要实机测量。

## 操作与首轮测试

| 场景 | 操作 / 应看到的结果 |
| --- | --- |
| 独立模式 | 未运行 host，摇杆右启动；P12 播放单音旋律 |
| PC 选歌 | host 就绪后在 `PC SONGS` 用摇杆上/下选歌，右选择 |
| PC 开局 | `PC READY` 时再次向右；电脑播放歌曲，设备显示音符 |
| 暂停 / 恢复 | 游戏中摇杆左暂停，右恢复；暂停菜单下退出 |
| 结果页 | 摇杆左返回菜单 |
| 独立局中启动 host | 当前独立局继续；结果页返回菜单后才进入 PC 曲库 |
| 关闭 host | 终端按 Ctrl+C；PC 音频停止，设备约 2.5 秒后回独立菜单 |
| PC 暂停时关闭 host | 同样回独立菜单，不停留在暂停页 |
| 重新运行 host | 重新握手，菜单恢复 PC 曲库；新局重新开始 |

第一次建议依次测试：独立开局 → 暂停退出 → 启动 host → PC 开局 → 暂停时关闭 host → 确认回独立菜单。确认后再测试 USB 拔线；拔掉 USB 后 GamePad 必须仍有电池或其他供电，否则设备会直接关机。

两种模式保留原有节奏参数：独立版提前量 3000 ms、Perfect/Good ±220/400 ms；PC 版提前量 1700 ms、Perfect/Good ±100/210 ms。RGB 统一使用数字输出，P0/P1 专供摇杆。初版两种模式的 Miss 都触发振动。方向键映射保持不变；之前外接左键未识别的问题见[硬件记录](../../docs/hardware-testing.md)，需要实机单独复核。

## 内存修正版（2026-11-04）

请重新从本地打开/导入 `deploy/main.py` 再发送；编辑器已经打开的旧代码不会随本地文件自动更新。

- 字体使用共享的 205 字节行数据，避免每次 `text()` 都创建 41 项字典和字形元组。
- 解包后的 3,010 字节旋律仅在独立游戏开始时分配，退出或结束后释放；菜单和 PC 模式不解包旋律。
- Base64 与 LZ 解码直接返回 `bytearray`，取消返回时的整块 `bytes` 复制，降低解包峰值。
- OLED 全屏与局部刷新共用代码；页面切换及通信轮询定期回收临时对象，空闲串口不再重复创建接收列表。

直接编译整个合并程序会耗尽编译期 RAM，因此 RAM2 的入口仅编译一个小启动器，再从自身文件读取注释载荷，分块执行并回收临时对象。分块保持完整的顶层语句，最大块不超过 4,000 bytes；整个过程只读取 `main.py`，不提取额外文件。

真实设备的 RAM 诊断中，菜单剩余约 35 KB，旋律加载后约 32 KB，释放后恢复约 35 KB；自动暂停退出正常。随后用户确认手动重刷 RAM2 后正常。具体诊断和待验收项见[硬件记录](../../docs/hardware-testing.md)。

## 源码、构建与测试

- `src/microbit_main.py`：共同 OLED/输入/判定引擎、本地音频和 PC 后端、实际串口适配器。
- `connection.py`：两端会话租约和菜单切换规则；设备适配器传入 `utime.ticks_diff`。
- `protocol.py`：60 字节有界分帧及编码。
- `pc_host.py`：PC 曲库、音频与可靠串口循环。仅此 host 兼容合并版 RH1 协议，原 `pc_player.py` 不兼容。
- `tools/build.py`：复用独立版的内嵌资源，打包成一个设备文件；不连接硬件。
- `tests/`：状态、协议、真实源码的整局模拟，以及实际压缩文件的模拟启动与双模式运行。

```sh
python3 projects/unified/tools/build.py
python3 -m unittest discover -s projects/unified/tests -v
```

构建仅需标准库：歌曲压缩数据改用 Base64，频率表只保留实际音高；标识符缩短和空白压缩有可逆 AST 检查，分块还会检查重新拼接后的 AST 一致。构建会更新源码的生成资源块与 `deploy/main.py`，目前设置 20,000 bytes 的生成文件上限。Python 3.13 为生成快照的参考环境。

串口为 115200 baud。host 每次仅发送一帧，收到 ACK 才继续；超时重发由设备按序去重。设备事件同样有序号、确认和重发，防止丢失暂停或开始消息。会话失效时轮换 challenge，旧会话帧不能启用 PC。host 不再边转换歌曲边占用串口，也不使用阻塞的谱面批次 sleep。

桌面模拟覆盖状态、协议、整局计分和实际单文件启动；实机仍需检查完整 PC 音画同步、连续切换、输入和音色。详细设计见[合并计划](../../docs/unification-plan.md)。
