"""一键打包 VirtualCom 为 Windows 可执行文件。

用法：
    python build.py
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ICON = ASSETS / "app.ico"
MAIN = ROOT / "main.py"


def ensure_icon() -> None:
    if ICON.exists():
        return
    print("[1/3] 生成应用图标 ...")
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_icon.py")], check=True)


def ensure_pyinstaller() -> None:
    if importlib.util.find_spec("PyInstaller") is not None:
        return
    print("[2/3] 安装 PyInstaller ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"], check=True)


def remove_existing_exe() -> None:
    exe = ROOT / "dist" / ("VirtualCom.exe" if sys.platform == "win32" else "VirtualCom")
    if not exe.exists():
        return
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "del", "/f", "/q", str(exe)], check=False)
    else:
        exe.unlink(missing_ok=True)


def build() -> None:
    ensure_icon()
    ensure_pyinstaller()
    remove_existing_exe()

    import PyInstaller.__main__

    print("[3/3] 正在打包 ...")
    args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "VirtualCom",
        "--icon",
        str(ICON),
        "--add-data",
        f"{ASSETS}{os.pathsep}assets",
        "--hidden-import",
        "PySide6.QtCore",
        "--hidden-import",
        "PySide6.QtGui",
        "--hidden-import",
        "PySide6.QtWidgets",
        "--hidden-import",
        "PySide6.QtSvg",
        "--hidden-import",
        "serial.tools.list_ports",
        "--hidden-import",
        "serial",
        str(MAIN),
    ]
    for installer in sorted(ROOT.glob("Setup_com0com*.exe")):
        args.extend(["--add-data", f"{installer}{os.pathsep}."])
    if sys.platform == "win32":
        args.insert(4, "--uac-admin")

    PyInstaller.__main__.run(args)
    exe = ROOT / "dist" / ("VirtualCom.exe" if sys.platform == "win32" else "VirtualCom")
    print("")
    print("打包完成：" + str(exe))


if __name__ == "__main__":
    build()
