# 硬件验证记录

记录日期：2026-11-03。设备为 micro:bit V2 和 GE1354 GamePad。后续统一使用 Chrome 的 [micro:bit Python Editor](https://python.microbit.org/) 导入设备 Python 文件并手动刷入。

## 已确认

- Standalone 可显示 MEGALOVANIA / READY、启动并基本正常游玩。
- 摇杆四个方向已通过原始输入诊断。早期运行时出现过 P0 返回 `-1002` 的问题；使用稳定运行时后恢复正常。
- 两版代码的方向键映射均为：上 P13、右 P11、下 P15、左 P5，低电平表示按下。
- P5 与 micro:bit 本体 A 按钮共用，P11 与本体 B 按钮共用。

## 暂停待查的方向键问题

- 用户反馈 Standalone 的 GamePad 左方向键无法判定，其余操作基本正常。
- 按住 GamePad 左键时，P13/P11/P15/P5 均保持高电平；其他候选输入脚扫描也未发现按下变化。
- 按住 micro:bit 本体 A 时，Button A 状态为 True，P5 变低，说明本体 A 和 P5 读取通路正常。
- 当时复现游戏的上拉、LED、音频初始化后，四个方向键引脚空闲电平正常。
- 用户另反馈此前 PC 版右键无法判定；当时运行时版本未核实，尚未在统一手动刷入流程下复测。

现有证据偏向 GamePad 外接左键的按键或接触通路，但尚未确定损坏。尚未针对该问题修改游戏核心代码。

下一步是断电后重新端正插紧 micro:bit 与 GamePad，再复测左键能否将 P5 拉低。用户尚未确认完成重插；硬件诊断保持暂停。

两版均还需要完整实机验收：方向键、摇杆、双 OLED、暂停恢复、计分，以及 PC 版串口音频同步或 Standalone 的 P12 声音、振动。

完整的历史开发进度已归档到本地 `local-assets/notes/PROGRESS-2026-11-03.md`，该目录由 Git 忽略。
