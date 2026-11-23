from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .constants import APP_NAME, CONFIG_FILE
from .logger import get_logger
from .models import AppSettings, ConfigDocument, PairConfig
from .utils import normalize_port

log = get_logger()


def config_directory() -> Path:
    base = os.getenv("APPDATA")
    path = Path(base) / APP_NAME if base else Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_directory() / CONFIG_FILE


class ConfigManager:
    def __init__(self) -> None:
        self.path = config_path()
        self.document = self._load()

    def _load(self) -> ConfigDocument:
        if not self.path.exists():
            return ConfigDocument()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return ConfigDocument.from_dict(raw)
        except Exception as exc:
            log.warning("配置文件读取失败，将使用备份并载入默认配置: %s", exc)
            try:
                shutil.copy2(self.path, self.path.with_suffix(".json.bak"))
            except Exception:
                pass
            return ConfigDocument()

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix="vc-", suffix=".json", dir=str(self.path.parent))
            os.close(fd)
            tmp = Path(tmp_name)
            tmp.write_text(
                json.dumps(self.document.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
            return True
        except Exception as exc:
            log.error("保存配置失败: %s", exc)
            return False

    @property
    def settings(self) -> AppSettings:
        return self.document.settings

    @property
    def pairs(self) -> list[PairConfig]:
        return self.document.pairs

    def find_pair(self, pair_id: str) -> PairConfig | None:
        return next((p for p in self.pairs if p.id == pair_id), None)

    def add_pair(self, pair: PairConfig) -> bool:
        self.pairs.append(pair)
        return self.save()

    def update_pair(self, pair: PairConfig) -> bool:
        for index, current in enumerate(self.pairs):
            if current.id == pair.id:
                self.pairs[index] = pair
                return self.save()
        return False

    def remove_pair(self, pair_id: str) -> PairConfig | None:
        pair = self.find_pair(pair_id)
        if pair:
            self.pairs.remove(pair)
            self.save()
        return pair

    def clear_pairs(self) -> None:
        self.pairs.clear()
        self.save()

    def update_settings(self, **kwargs: Any) -> bool:
        for key, value in kwargs.items():
            if not hasattr(self.settings, key):
                continue
            if key in {"port_min", "port_max"}:
                value = int(value)
            setattr(self.settings, key, value)
        return self.save()

    def reset_settings(self) -> None:
        self.document.settings = AppSettings()
        self.save()

    def is_port_used(self, port: str, exclude_id: str = "") -> bool:
        target = normalize_port(port)
        return any(
            p.id != exclude_id and target in (normalize_port(p.port_a), normalize_port(p.port_b))
            for p in self.pairs
        )
