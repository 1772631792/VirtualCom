from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from .constants import MAX_PORT_NUMBER


def normalize_port(value: str) -> str:
    text = str(value or "").strip().upper().replace(" ", "")
    if not text:
        return ""
    if not text.startswith("COM"):
        digits = "".join(ch for ch in text if ch.isdigit())
        return "COM" + digits if digits else text
    digits = "".join(ch for ch in text[3:] if ch.isdigit())
    return "COM" + digits if digits else text


def is_valid_port(value: str) -> bool:
    text = normalize_port(value)
    return bool(re.fullmatch(r"COM([1-9]\d*)", text)) and int(text[3:]) <= MAX_PORT_NUMBER


def port_number(value: str) -> int:
    text = normalize_port(value)
    return int(text[3:]) if text.startswith("COM") and text[3:].isdigit() else -1


def list_physical_ports() -> set[str]:
    try:
        from serial.tools import list_ports

        return {normalize_port(p.device) for p in list_ports.comports() if p.device}
    except Exception:
        return set()


def suggest_ports(count: int, excluded: Iterable[str], port_min: int = 1, port_max: int = 64) -> list[str]:
    used = {normalize_port(p) for p in excluded} | list_physical_ports()
    candidates = [
        f"COM{i}"
        for i in range(max(1, port_min), min(MAX_PORT_NUMBER, port_max) + 1)
        if f"COM{i}" not in used
    ]
    return candidates[:count]


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_command(
    args: list[str],
    timeout: int = 12,
    cwd: str | Path | None = None,
) -> tuple[int, str, str]:
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=flags,
            cwd=str(cwd) if cwd else None,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except FileNotFoundError:
        return -1, "", "找不到可执行文件: " + args[0]
    except OSError as exc:
        return -1, "", str(exc)


def open_path(path: str | Path) -> bool:
    try:
        p = Path(path)
        if sys.platform == "win32":
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return True
    except Exception:
        return False


def friendly_error(exc: BaseException) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__
