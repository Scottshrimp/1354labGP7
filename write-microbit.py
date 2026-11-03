#!/usr/bin/env python3
"""Package and flash either rhythm game using uflash 2.0."""

import argparse
import ast
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SOURCES = {
    "pc": ROOT / "projects/pc-integrated/microbit_main.py",
    "standalone": ROOT / "projects/standalone/src/deploy/main.py",
}


def load_uflash():
    """Use the project's virtual environment without requiring activation."""
    try:
        import uflash
    except ModuleNotFoundError:
        venv = ROOT / ".venv"
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if python.is_file() and Path(sys.prefix).resolve() != venv.resolve():
            os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
        raise RuntimeError(
            "缺少 uflash。请先运行：\n"
            "  python3 -m venv .venv\n"
            "  .venv/bin/python -m pip install uflash==2.0.0\n"
            "Windows 安装命令：.venv\\Scripts\\python -m pip install uflash==2.0.0"
        ) from None
    if tuple(int(p) for p in uflash.get_version().split(".")[:2]) < (2, 0):
        raise RuntimeError("micro:bit V2 需要 uflash 2.0+，请升级 uflash。")
    return uflash


def choose_version(parser):
    if not sys.stdin.isatty():
        parser.error("请指定版本：pc 或 standalone。")
    print("选择要刷入的版本：\n  1. PC 整合版 v4.1\n  2. Standalone 独立运行版")
    while True:
        choice = input("输入 1 或 2（Ctrl+C 取消）：").strip().lower()
        if choice in ("1", "pc"):
            return "pc"
        if choice in ("2", "standalone"):
            return "standalone"
        print("请输入 1 或 2。")


def device_mount(uflash, requested):
    found = str(requested) if requested else uflash.find_microbit()
    if not found:
        raise RuntimeError("未找到 MICROBIT 挂载盘。请连接 USB 数据线，或用 --mount 指定路径。")
    mount = Path(found).expanduser().resolve()
    details = mount / "DETAILS.TXT"
    if not details.is_file() or "DAPLink" not in details.read_text(errors="replace"):
        raise RuntimeError(f"目标目录不是 DAPLink 设备挂载盘：{mount}")
    return mount


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="刷写 GE1354 micro:bit 游戏；不指定版本时显示选择菜单。",
        epilog="示例：./write-microbit.py pc  或  ./write-microbit.py standalone --hex-only",
    )
    parser.add_argument("version", nargs="?", choices=SOURCES, help="pc：PC 整合版；standalone：独立版")
    parser.add_argument("--mount", type=Path, help="MICROBIT 挂载路径（默认自动查找）")
    parser.add_argument("--hex-only", action="store_true", help="只在 build/hex/ 中生成 HEX，不写入设备")
    args = parser.parse_args(argv)
    uflash = load_uflash()
    version = args.version or choose_version(parser)
    source = SOURCES[version]
    script = source.read_bytes()
    ast.parse(script, filename=str(source))
    # Resolve and validate the device before doing any flash writes.
    mount = None if args.hex_only else device_mount(uflash, args.mount)
    hex_data = uflash.embed_fs_uhex(uflash._RUNTIME, script)
    folder = "pc-integrated" if version == "pc" else "standalone"
    output = ROOT / "build/hex" / folder / source.with_suffix(".hex").name
    output.parent.mkdir(parents=True, exist_ok=True)
    uflash.save_hex(hex_data, str(output))
    print(f"程序：{source.relative_to(ROOT)}（{len(script)} bytes）")
    print(f"HEX：{output}")
    if args.hex_only:
        print("仅生成 HEX，未写入设备。")
        return 0

    target = mount / "micropython.hex"
    print(f"正在写入：{target}（替换设备当前程序）", flush=True)
    uflash.save_hex(hex_data, str(target))
    print("HEX 已发送，请等待设备刷写并重启；刷写期间请勿拔线。")
    if version == "pc":
        print("PC 版还需启动电脑端 pc_player.py，并指定设备串口。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\n已取消。", file=sys.stderr)
        sys.exit(130)
    except (OSError, RuntimeError, ValueError, SyntaxError) as error:
        print(f"错误：{error}", file=sys.stderr)
        sys.exit(1)
