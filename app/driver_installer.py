from __future__ import annotations

import ctypes
import os
import platform
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .resources import resource_path
from .utils import is_admin, run_command

X64_INSTALLER = "Setup_com0com_v3.0.0.0_W7_x64_signed.exe"
X86_INSTALLER = "Setup_com0com_v3.0.0.0_W7_x86_signed.exe"
DRIVER_FILES = (
    "com0com.inf",
    "cncport.inf",
    "comport.inf",
    "com0com.cat",
    "com0com.sys",
)


@dataclass
class InstallResult:
    ok: bool
    message: str
    setupc_path: str = ""


def installer_name() -> str:
    machine = platform.machine().lower()
    return X86_INSTALLER if machine in {"x86", "i386", "i686"} else X64_INSTALLER


def bundled_installer() -> Path:
    return resource_path(installer_name())


def find_setupc() -> str:
    candidates: list[Path] = []
    for env in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
        root = Path(os.environ.get(env, ""))
        if not str(root) or not root.exists():
            continue
        candidates.extend(root.glob("com0com*/setupc.exe"))
        candidates.append(root / "com0com" / "setupc.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return ""


def ensure_inf_files(setupc_path: str) -> tuple[bool, str]:
    """修复官方安装包漏复制到 System32 的 INF/CAT/SYS 文件。"""
    source_dir = Path(setupc_path).resolve().parent
    system32 = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32"
    copied: list[str] = []
    for name in DRIVER_FILES:
        source = source_dir / name
        if not source.is_file():
            continue
        target = system32 / name
        try:
            if not target.is_file() or source.stat().st_size != target.stat().st_size:
                shutil.copy2(source, target)
                copied.append(name)
        except Exception as exc:
            return False, f"无法复制驱动文件 {name} 到 System32：{exc}。请以管理员身份运行软件。"
    if copied:
        return True, "已补齐驱动文件：" + "、".join(copied)
    return True, ""


def install_com0com(
    timeout: int = 180,
    on_step: Callable[[str], None] | None = None,
) -> InstallResult:
    """静默安装内置的官方签名 com0com 驱动包。"""

    def step(text: str) -> None:
        if on_step:
            on_step(text)

    if sys.platform != "win32":
        return InstallResult(False, "当前系统不是 Windows，无法安装 com0com。")

    existing = find_setupc()
    if existing:
        ok, detail = ensure_inf_files(existing)
        if not ok:
            return InstallResult(False, detail, existing)
        text = "com0com 已经安装。" + (detail if detail else "无需重复安装。")
        return InstallResult(True, text, existing)

    installer = bundled_installer()
    if not installer.is_file():
        return InstallResult(
            False,
            "安装包缺失。请确认 tools/com0com 目录里有官方签名安装包，或重新下载 build 产物。",
        )

    if is_admin():
        step("正在静默安装 com0com 驱动 ...")
        rc, out, err = run_command([str(installer), "/S"], timeout=timeout)
        if rc not in (0,):
            detail = (out + " " + err).strip()
            return InstallResult(False, detail or f"安装程序退出码：{rc}")
    else:
        step("正在请求管理员权限 ...")
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", str(installer), "/S", None, 1
            )
        except Exception as exc:
            return InstallResult(False, f"无法启动安装程序：{exc}")
        if int(result) <= 32:
            return InstallResult(False, "你取消了管理员授权，驱动没有安装。")

    step("等待驱动写入系统 ...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = find_setupc()
        if found:
            ok, detail = ensure_inf_files(found)
            if not ok:
                return InstallResult(False, detail, found)
            step("驱动安装完成。")
            message = "com0com 驱动安装完成。" + (detail if detail else "")
            return InstallResult(True, message, found)
        time.sleep(0.7)

    return InstallResult(
        False,
        "安装程序已执行，但没有检测到 setupc.exe。请重启电脑后再打开软件，或手动检查 com0com 是否安装成功。",
    )
