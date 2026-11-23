from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .config import ConfigManager
from .logger import get_logger
from .models import PairConfig
from .utils import is_admin, is_valid_port, normalize_port, run_command

log = get_logger()


@dataclass
class DriverPair:
    id: str
    partner_id: str
    port_a: str
    port_b: str

    @property
    def ports(self) -> tuple[str, str]:
        return self.port_a, self.port_b

    def contains(self, port: str) -> bool:
        return normalize_port(port) in self.ports


@dataclass
class BackendResult:
    ok: bool
    message: str = ""
    driver_pair: DriverPair | None = None


@dataclass
class BackendStatus:
    available: bool
    setupc_path: str
    admin: bool
    pairs: list[DriverPair] = field(default_factory=list)
    message: str = ""


class Com0comBackend:
    """通过 com0com 的 setupc.exe 管理真正的 Windows 虚拟串口对。"""

    def __init__(self, config: ConfigManager) -> None:
        self.config = config
        self.setupc_path = self.autodetect()

    @staticmethod
    def _candidate_paths() -> list[str]:
        paths: list[str] = []
        configured = os.getenv("COM0COM_PATH")
        if configured:
            paths.append(configured)
        for env in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
            root = os.getenv(env)
            if not root:
                continue
            paths.append(str(Path(root) / "com0com" / "setupc.exe"))
            paths.extend(str(p) for p in Path(root).glob("com0com*/setupc.exe"))
            paths.extend(str(p) for p in Path(root).glob("com0com*/setupc64.exe"))
        local = Path(__file__).resolve().parents[1] / "tools" / "com0com" / "setupc.exe"
        paths.append(str(local))
        return paths

    def autodetect(self) -> str:
        configured = self.config.settings.setupc_path.strip()
        if configured and Path(configured).is_file():
            return str(Path(configured).resolve())

        for candidate in self._candidate_paths():
            if candidate and Path(candidate).is_file():
                return str(Path(candidate).resolve())
        return configured

    @property
    def available(self) -> bool:
        return bool(self.setupc_path) and Path(self.setupc_path).is_file()

    def refresh_path(self) -> str:
        self.setupc_path = self.autodetect()
        return self.setupc_path

    def status(self) -> BackendStatus:
        pairs: list[DriverPair] = []
        message = ""
        if not self.available:
            message = "未检测到 com0com 驱动，请在设置中指定 setupc.exe 路径。"
        else:
            result = self._call("list")
            if result.ok:
                pairs = self.parse_list(result.message)
            else:
                message = result.message
        return BackendStatus(
            available=self.available,
            setupc_path=self.setupc_path,
            admin=is_admin(),
            pairs=pairs,
            message=message,
        )

    @dataclass
    class _CallResult:
        ok: bool
        message: str

    def _call(self, *args: str) -> _CallResult:
        if not self.available:
            return self._CallResult(False, "未找到 setupc.exe，请先安装 com0com 或在设置中指定路径。")
        rc, out, err = run_command(
            [self.setupc_path, *args],
            timeout=30,
            cwd=Path(self.setupc_path).resolve().parent,
        )
        text = "\n".join(part.strip() for part in (out, err) if part.strip())
        lowered = text.lower()
        if rc != 0 or "error" in lowered or "usage:" in lowered:
            return self._CallResult(False, text or f"setupc 退出码: {rc}")
        return self._CallResult(True, text)

    @staticmethod
    def parse_list(output: str) -> list[DriverPair]:
        pattern = re.compile(r"^\s*(CNC[A-Za-z]\d+)\s+PortName=([^,;\s]+)", re.I)
        found: dict[str, str] = {}
        for line in output.splitlines():
            match = pattern.match(line)
            if not match:
                continue
            found[match.group(1).upper()] = normalize_port(match.group(2))

        pairs: list[DriverPair] = []
        for identifier in sorted(found):
            if not identifier.startswith("CNCA"):
                continue
            suffix = identifier[4:]
            partner = "CNCB" + suffix
            if partner not in found:
                continue
            pairs.append(
                DriverPair(
                    id=identifier,
                    partner_id=partner,
                    port_a=found[identifier],
                    port_b=found[partner],
                )
            )
        return pairs

    def list_pairs(self) -> list[DriverPair]:
        result = self._call("list")
        if not result.ok:
            log.warning("读取 com0com 端口失败: %s", result.message)
            return []
        return self.parse_list(result.message)

    def busynames(self) -> set[str]:
        """返回 com0com 报告为已占用的 COM 名（包括 COMDB 里的残留占用）。"""
        result = self._call("busynames", "COM?*")
        if not result.ok:
            return set()
        return {
            normalize_port(match.group(0))
            for match in re.finditer(r"COM\d+", result.message, re.I)
        }

    def find_driver_pair(self, pair: PairConfig, pairs: Iterable[DriverPair] | None = None) -> DriverPair | None:
        all_pairs = list(pairs) if pairs is not None else self.list_pairs()
        if pair.driver_id:
            for item in all_pairs:
                if item.id.upper() == pair.driver_id.upper() or item.partner_id.upper() == pair.driver_id.upper():
                    return item
        for item in all_pairs:
            if {normalize_port(pair.port_a), normalize_port(pair.port_b)} == set(item.ports):
                return item
        return None

    def install(self, pair: PairConfig) -> BackendResult:
        a, b = normalize_port(pair.port_a), normalize_port(pair.port_b)
        if not is_valid_port(a) or not is_valid_port(b) or a == b:
            return BackendResult(False, "端口名无效或两端相同，请选择两个不同的 COM 口。")
        if not self.available:
            return BackendResult(False, "未找到 setupc.exe。请先安装 com0com，或在「系统设置」里选择它的路径。")

        existing = self.list_pairs()
        used = [p for p in existing if p.contains(a) or p.contains(b)]
        if used:
            names = ", ".join(f"{p.port_a}↔{p.port_b}" for p in used)
            return BackendResult(False, f"端口已被占用: {names}")

        result = self._call("install", f"PortName={a}", f"PortName={b}")
        if not result.ok:
            return BackendResult(False, result.message)

        created = None
        for item in self.list_pairs():
            if set(item.ports) == {a, b}:
                created = item
                break
        return BackendResult(True, f"已在驱动中创建 {a} ↔ {b}", created)

    def remove(self, pair: PairConfig) -> BackendResult:
        if not self.available:
            return BackendResult(False, "未找到 setupc.exe，无法删除驱动端口。")
        existing = self.list_pairs()
        driver_pair = self.find_driver_pair(pair, existing)
        if not driver_pair:
            return BackendResult(True, "驱动中没有该串口对，已仅删除本地配置。")

        match = re.search(r"(\d+)$", driver_pair.id, re.I)
        if not match:
            return BackendResult(False, f"无法识别端口对编号：{driver_pair.id}")
        number = match.group(1)
        result = self._call("remove", number)
        if not result.ok:
            return BackendResult(False, result.message)
        return BackendResult(True, f"已移除虚拟端口 {driver_pair.port_a} ↔ {driver_pair.port_b}")
