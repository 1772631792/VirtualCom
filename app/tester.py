from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .utils import normalize_port


@dataclass
class TestResult:
    ok: bool
    title: str
    detail: str


def run_loopback(
    port_a: str,
    port_b: str,
    baudrate: int = 115200,
    on_step: Callable[[str], None] | None = None,
) -> TestResult:
    """两端互发一段数据，验证 com0com 串口对是否真正连通。"""

    def step(text: str) -> None:
        if on_step:
            on_step(text)

    try:
        import serial
    except ImportError:
        return TestResult(False, "缺少依赖", "请先安装 pyserial: pip install pyserial")

    a, b = normalize_port(port_a), normalize_port(port_b)
    step(f"正在打开 {a} 与 {b} ...")
    try:
        with serial.Serial(a, baudrate=baudrate, timeout=0.6) as sa, serial.Serial(
            b, baudrate=baudrate, timeout=0.6
        ) as sb:
            sa.reset_input_buffer()
            sb.reset_input_buffer()
            time.sleep(0.05)

            payload_a = f"PING-FROM-{a}-{int(time.time() * 1000)}".encode("ascii")
            step(f"{a} → {b} 发送 {len(payload_a)} 字节 ...")
            sa.write(payload_a)
            got_b = _read_exact(sb, len(payload_a), 1.5)

            if got_b != payload_a:
                return TestResult(
                    False,
                    "单向测试失败",
                    f"{b} 收到 {len(got_b)} 字节，与发送内容不一致。请确认端口未被其他程序占用。",
                )

            payload_b = b"PONG-OK"
            step(f"{b} → {a} 发送回执 ...")
            sb.write(payload_b)
            got_a = _read_exact(sa, len(payload_b), 1.5)

            if got_a != payload_b:
                return TestResult(False, "双向测试失败", f"{a} 未收到正确回执。")

            return TestResult(
                True,
                "回环测试通过",
                f"{a} ↔ {b} 双向收发正常，波特率 {baudrate}。",
            )
    except Exception as exc:
        return TestResult(False, "无法打开串口", str(exc))


def _read_exact(ser, size: int, timeout: float) -> bytes:
    buffer = bytearray()
    deadline = time.monotonic() + timeout
    while len(buffer) < size and time.monotonic() < deadline:
        chunk = ser.read(size - len(buffer))
        if chunk:
            buffer.extend(chunk)
        else:
            time.sleep(0.01)
    return bytes(buffer)
