# Unified Rhythm Hit · 实机测试版

一个 micro:bit V2 程序加一个 PC host。无 host 时可从独立曲库选歌。host 准备就绪后，在菜单切换到 PC 曲库。PC 断线时结束当前局，约 2.5 秒后回到独立菜单。

当前为 **RAM2 分块编译测试版**。用户已确认重新刷入后正常，原先启动时的 `MemoryError` 已解决。完整 PC 音画同步和连续切换仍需实机验收；原有 `pc-integrated/` 和 `standalone/` 保留作基线。刷入使用 Chrome Python Editor。

## 此分支：AP / FC 指示灯

分支 `codex/led-ap-fc` 将游戏中的 5×5 阵列用于当前整局状态：

| 状态 | 判定条件 | LED |
| --- | --- | --- |
| AP（All Perfect） | 尚无 Good 或 Miss | 25 颗全亮 |
| FC（Full Combo），非 AP | 已有 Good，但没有 Miss | 最外圈 16 颗亮 |
| FC 已断 | 至少一次 Miss，包括 PC 模式的错误方向 | 全灭 |

状态按整局累计，连击恢复不会重新亮起；每次新开局重新计算。倒计时保留 3/2/1，歌曲开始后切换为指示灯；暂停与恢复保持灯态，不显示连击数字或暂停方框。结果页保留最终状态，返回菜单后恢复菜单表情。PC 和独立模式都生效。

本分支从 RAM2 主线独立开发，不包含进度灯实验。测试覆盖 AP → FC → 断 FC、全 Perfect、错误方向、暂停及新局重置；新灯态仍待手动刷入实测。

## 先刷入一个文件

1. 让摇杆回中，用 USB 连接 micro:bit V2 和 GamePad。
2. 在 Chrome 打开 [micro:bit Python Editor](https://python.microbit.org/)。
3. 在一个干净的编辑器项目中打开/导入 **[deploy/main.py](deploy/main.py)**，点击 **Send to micro:bit**。只需要这个文件，不需要把源码模块逐个添加到编辑器。
4. 未启动 host 时，右 OLED 显示 `STANDALONE` 曲库，左 OLED 显示 `READY`。摇杆上/下选歌，向右开始。

独立曲库包含两首歌，通过 `music.pitch()` 在 P12 逐个播放音符。旋律和谱面共用游戏时钟。

- `MEGALOVANIA` 保留原旋律与谱面的前约 1 分 55 秒，在乐句停顿处结束。
- `MARIO GROUND THEME` 从视频音轨提取主旋律，约 1 分 5 秒，有 49 个对齐旋律起音的单键提示。

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

## 双人模式

给两块 micro:bit 都刷入本分支的 `deploy/main.py`，断开 Python Editor 的串口连接，再把两块板接到同一台 PC。PC 使用同一套本地曲库与音频依赖。

```sh
python3 projects/unified/multiplayer.py
```

浏览器打开 [双人控制台](http://127.0.0.1:8765/)。设备较多时，可以重复传入 `--port` 指定两个串口，参数顺序对应玩家 1 和玩家 2。`--songs`、`--offset-ms` 和 `--web-port` 可分别指定曲库、音频补偿和网页端口。

1. 两块板都进入联机菜单后，网页显示 `Ready` 并开放选曲。
2. 在网页选择并确认一首歌。网页切为实时显示，两块板分别加载谱面。
3. 在两块板上各自向右按 Ready。先确认的一方等待，双方确认后 host 自动安排同一时刻开场。音乐由 PC 播放，网页显示共同进度和各人的分数。
4. 两人的本局成绩在网页结算。各自在板上向左返回后，网页重新开放选曲。

结算显示整局最大连击，由设备在 `DONE` 中提交；未重刷的旧固件仍可连接，最大连击改由 200 ms 遥测估算，可能略低于实际值。倒计时前同步失败会取消开场。对局中一块板掉线时，另一位继续游玩，掉线玩家在本局标记为未完赛。多人模式没有个人暂停，历史排行榜留待后续。

## 纯网页版双人模式

网站统一使用 `web/style.css` 的亮色样式。教程入口预留在 `/tutorial/`，后续页面沿用同一份样式。

从仓库根目录构建并启动本地预览。

```sh
python3 projects/unified/tools/build_web.py
python3 -m http.server 8875 --bind 127.0.0.1 --directory projects/unified/dist
```

在桌面 Chrome 或 Edge 打开 [http://127.0.0.1:8875/](http://127.0.0.1:8875/)。两台 micro:bit V2 都用 Python Editor 刷入网页提供的 `main.py`，刷后关闭编辑器串口，再用 USB 数据线把两块板接到同一台电脑。首次分别点击 **Connect player 1** 和 **Connect player 2** 授权。网页会自动尝试连接浏览器已授权且能明确分配的设备。端口被占用时，关闭本地 Python host 和其他正在连接的标签页。

两块板进入联机大堂后，在网页选歌并确认。两位玩家各自在设备上向右 Ready。打完后都向左返回，再试一局。网页提供下载的 `main.py` 直接复制自已提交的 `deploy/main.py`，与本地刷入文件逐字节相同，单机菜单保留 MEGALOVANIA 和 MARIO GROUND THEME。网页曲库的 **STARTER BEAT** 由构建脚本生成，其余歌曲见下文。

线上站点为 `https://rhythmhit.scottshrimp.com`，托管在 VPS3 的 Caddy 上（站点块见仓库根目录 `deploy/Caddyfile.rhythmhit`）。发布流程与主站一致：本地开发并 push，再在服务器拉取指定 commit 构建：

```sh
ssh root@45.32.60.198 rhythmhit-deploy <完整 commit>
```

网页曲库包含 STARTER BEAT 和 `../pc-integrated/songs/` 中已准备网页音频的歌曲。新增或替换歌曲音频后，在 Mac 上先让 `pc_host.py --check` 更新 `cache.wav`，再运行 `python3 projects/unified/tools/web_audio.py`。它用 afconvert 把 `cache.wav` 编码为带内容哈希的 `media/<id>-<hash>.m4a`（不进 Git），并写入 `song.json` 的 `web_audio`；Chrome 解码结果与 `cache.wav` 逐采样对齐，谱面无需调整。发布前先上传音频：

```sh
scp projects/unified/media/*.m4a root@45.32.60.198:/srv/rhythmhit/media/
```

音频由 Caddy 从 `/srv/rhythmhit/media` 长期缓存提供；发布命令发现缺少音频时会拒绝切换。

`deploy/rhythmhit-deploy.sh` 以 `nobody` 身份运行 `build_web.py`，产物装入 `/srv/rhythmhit/releases/<commit>` 并原子切换 `current`；HTTPS 检查失败时自动回到上一版，保留最近 5 个版本。教程页源文件为 `web/tutorial/index.html`。访客的对局和串口通信由网页所在的浏览器处理。先验证 macOS 与 Windows 上的首次授权、刷新自动连接、连续两局、曲首与曲末的音画同步，以及对局中拔掉一块板后的结算。

浏览器协议回归可以用 Node.js 运行，测试会让 JavaScript host 与两个固件模拟实例完成对局。

```sh
python3 projects/unified/tools/build_web.py
node --test projects/unified/tests/test_browser_host.mjs
```

## 操作与首轮测试

| 场景 | 操作 / 应看到的结果 |
| --- | --- |
| 独立模式 | 未运行 host，摇杆上/下选歌，右开始。P12 播放单音旋律 |
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

直接编译整个合并程序会耗尽编译期 RAM，因此 RAM2 的入口仅编译一个小启动器，再从自身文件读取注释载荷，按需解压后分块执行并回收临时对象。分块保持完整的顶层语句，解压后的最大块不超过 4,000 bytes。整个过程只读取 `main.py`。

真实设备的 RAM 诊断中，菜单剩余约 35 KB，旋律加载后约 32 KB，释放后恢复约 35 KB；自动暂停退出正常。随后用户确认手动重刷 RAM2 后正常。具体诊断和待验收项见[硬件记录](../../docs/hardware-testing.md)。

## 源码、构建与测试

- `src/microbit_main.py`：共同 OLED/输入/判定引擎、本地音频和 PC 后端、实际串口适配器。
- `connection.py`：两端会话租约和菜单切换规则；设备适配器传入 `utime.ticks_diff`。
- `protocol.py`：60 字节有界分帧及编码。
- `pc_host.py`：PC 曲库、音频与可靠串口循环。仅此 host 兼容合并版 RH1 协议，原 `pc_player.py` 不兼容。
- `multiplayer.py`、`web/`：双设备会话、时钟对齐与网页控制台。`T` 帧独立于可靠事件流，按 200 ms 上报一次累计状态。最终分数由可靠 `DONE` 提交。
- `music/mario-ground-theme.json` 包含马力欧主题的旋律和谱面。每个旋律事件包含开始毫秒数、时长毫秒数和 MIDI 音高。
- `tools/build.py` 复用独立版的 MIDI 转换和压缩，把独立曲库打包成一个设备文件。
- `tests/`：状态、协议、真实源码的整局模拟，以及实际压缩文件的模拟启动与双模式运行。

```sh
python3 projects/unified/tools/build.py
python3 -m unittest discover -s projects/unified/tests -v
```

构建仅需标准库。压缩曲目以 Base64 存储，开局时解包所选曲目的旋律和谱面。标识符缩短、空白压缩和编译分块都检查 AST 一致性。构建会更新源码的生成资源块与 `deploy/main.py`，上限为 20,000 bytes。Python 3.13 为生成快照的参考环境。

串口为 115200 baud。host 每次仅发送一帧，收到 ACK 才继续；超时重发由设备按序去重。设备事件同样有序号、确认和重发，防止丢失暂停或开始消息。会话失效时轮换 challenge，旧会话帧不能启用 PC。host 不再边转换歌曲边占用串口，也不使用阻塞的谱面批次 sleep。

桌面模拟覆盖状态、协议、整局计分和实际单文件启动；实机仍需检查完整 PC 音画同步、连续切换、输入和音色。详细设计见[合并计划](../../docs/unification-plan.md)。
