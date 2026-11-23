from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        root = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        root = Path(__file__).resolve().parents[1]
    return root / relative


def icon_path() -> Path:
    return resource_path("assets/app.ico")


def logo_path() -> Path:
    return resource_path("assets/logo.png")


def app_icon() -> QIcon:
    return QIcon(str(icon_path()))
