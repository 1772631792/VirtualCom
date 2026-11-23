from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .constants import DEFAULT_PORT_MAX, DEFAULT_PORT_MIN


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def _norm_port(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if not text.startswith("COM"):
        text = "COM" + text.lstrip("COM")
    digits = "".join(ch for ch in text[3:] if ch.isdigit())
    return "COM" + digits if digits else text


@dataclass
class PairConfig:
    id: str = field(default_factory=new_id)
    name: str = "未命名串口对"
    port_a: str = ""
    port_b: str = ""
    description: str = ""
    auto_create: bool = True
    driver_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    @property
    def port_pair(self) -> tuple[str, str]:
        return self.port_a, self.port_b

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PairConfig":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name") or "未命名串口对"),
            port_a=_norm_port(data.get("port_a")),
            port_b=_norm_port(data.get("port_b")),
            description=str(data.get("description") or ""),
            auto_create=bool(data.get("auto_create", True)),
            driver_id=str(data.get("driver_id") or ""),
            created_at=str(data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M")),
        )


@dataclass
class AppSettings:
    theme: str = "midnight"
    setupc_path: str = ""
    start_minimized: bool = False
    minimize_to_tray: bool = False
    auto_apply_on_start: bool = False
    show_notifications: bool = True
    driver_prompt_declined: bool = False
    port_min: int = DEFAULT_PORT_MIN
    port_max: int = DEFAULT_PORT_MAX

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        return cls(
            theme=str(data.get("theme") or "midnight"),
            setupc_path=str(data.get("setupc_path") or ""),
            start_minimized=bool(data.get("start_minimized", False)),
            minimize_to_tray=bool(data.get("minimize_to_tray", False)),
            auto_apply_on_start=bool(data.get("auto_apply_on_start", False)),
            show_notifications=bool(data.get("show_notifications", True)),
            driver_prompt_declined=bool(data.get("driver_prompt_declined", False)),
            port_min=int(data.get("port_min", DEFAULT_PORT_MIN)),
            port_max=int(data.get("port_max", DEFAULT_PORT_MAX)),
        )


@dataclass
class ConfigDocument:
    version: int = 3
    settings: AppSettings = field(default_factory=AppSettings)
    pairs: list[PairConfig] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "settings": self.settings.to_dict(),
            "pairs": [pair.to_dict() for pair in self.pairs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigDocument":
        pairs = []
        seen_ids: set[str] = set()
        for raw in data.get("pairs", []) or []:
            if not isinstance(raw, dict):
                continue
            pair = PairConfig.from_dict(raw)
            if pair.id in seen_ids:
                pair.id = new_id()
            if pair.port_a and pair.port_a == pair.port_b:
                continue
            seen_ids.add(pair.id)
            pairs.append(pair)
        version = int(data.get("version", 1) or 1)
        settings = AppSettings.from_dict(data.get("settings", {}) or {})
        if version < 2:
            if settings.port_min < DEFAULT_PORT_MIN:
                settings.port_min = DEFAULT_PORT_MIN
            if settings.port_max <= settings.port_min:
                settings.port_max = DEFAULT_PORT_MAX
            version = 2
        if version < 3:
            settings.minimize_to_tray = False
            version = 3
        return cls(version=version, settings=settings, pairs=pairs)
