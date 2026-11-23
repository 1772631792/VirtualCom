from __future__ import annotations

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ..backend import Com0comBackend
from ..config import ConfigManager
from ..driver_installer import install_com0com
from ..models import PairConfig
from ..tester import TestResult, run_loopback
from ..utils import is_valid_port, list_physical_ports, normalize_port, suggest_ports
from .icons import icon


class PairDialog(QDialog):
    def __init__(
        self,
        config: ConfigManager,
        pair: PairConfig | None = None,
        parent=None,
        backend: Com0comBackend | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.source = pair
        self.own_ports = {pair.port_a, pair.port_b} if pair else set()
        self.busy_ports = set(list_physical_ports())
        if backend and backend.available:
            self.busy_ports |= backend.busynames()
        self.setWindowTitle("新建串口对" if pair is None else "编辑串口对")
        self.setModal(True)
        self.setMinimumWidth(440)

        self.name_edit = QLineEdit(pair.name if pair else "")
        self.name_edit.setPlaceholderText("可选，留空会自动生成")
        self.description_edit = QLineEdit(pair.description if pair else "")
        self.description_edit.setPlaceholderText("可选，写点备注方便以后识别")

        self.port_a = QComboBox()
        self.port_b = QComboBox()
        for combo in (self.port_a, self.port_b):
            combo.setEditable(True)
            combo.addItems([f"COM{i}" for i in range(1, 257)])
            combo.setCurrentText("COM1")

        if pair:
            self.port_a.setCurrentText(pair.port_a)
            self.port_b.setCurrentText(pair.port_b)
        else:
            suggested = suggest_ports(
                2, self.busy_ports, config.settings.port_min, config.settings.port_max
            )
            if len(suggested) == 2:
                self.port_a.setCurrentText(suggested[0])
                self.port_b.setCurrentText(suggested[1])

        suggest_btn = QPushButton("推荐空闲端口")
        suggest_btn.setProperty("variant", "ghost")
        suggest_btn.setIcon(icon("refresh", "#7BE0D0", 15))
        suggest_btn.clicked.connect(self._suggest)

        port_row = QHBoxLayout()
        port_row.setSpacing(8)
        port_row.addWidget(self.port_a)
        port_row.addWidget(QLabel("↔"))
        port_row.addWidget(self.port_b)
        port_row.addWidget(suggest_btn)

        self.auto_create = QCheckBox("创建后立即写入驱动")
        self.auto_create.setChecked(pair.auto_create if pair else True)

        self.hint = QLabel()
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow(QLabel("名称（可选）"), self.name_edit)
        form.addRow(QLabel("端口"), port_row)
        form.addRow(QLabel("备注"), self.description_edit)
        form.addRow(QLabel(""), self.auto_create)
        form.addRow(QLabel(""), self.hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.button(QDialogButtonBox.Ok).setProperty("variant", "primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(16)
        title = QLabel("新建串口对" if pair is None else "编辑串口对")
        title.setObjectName("title")
        root.addWidget(title)
        root.addLayout(form)
        root.addWidget(buttons)

        self.port_a.currentTextChanged.connect(self._update_hint)
        self.port_b.currentTextChanged.connect(self._update_hint)
        self._update_hint()

    def _suggest(self) -> None:
        used = set(self.busy_ports)
        for p in self.config.pairs:
            if self.source and p.id == self.source.id:
                continue
            used.update((p.port_a, p.port_b))
        suggested = suggest_ports(
            2, used, self.config.settings.port_min, self.config.settings.port_max
        )
        if len(suggested) == 2:
            self.port_a.setCurrentText(suggested[0])
            self.port_b.setCurrentText(suggested[1])
            self.hint.setText("已选择两个当前未被占用的端口。")

    def _update_hint(self) -> None:
        notes = []
        for port in (normalize_port(self.port_a.currentText()), normalize_port(self.port_b.currentText())):
            if port in self.busy_ports and port not in self.own_ports:
                notes.append(f"{port} 已被系统或驱动标记为占用")
        self.hint.setText("；".join(notes) if notes else "提示：com0com 需要管理员权限才能创建端口。")

    def values(self) -> PairConfig:
        source = self.source
        pair = source or PairConfig()
        a = normalize_port(self.port_a.currentText())
        b = normalize_port(self.port_b.currentText())
        if a != pair.port_a or b != pair.port_b:
            pair.driver_id = ""
        pair.name = self.name_edit.text().strip() or f"{a} ↔ {b}"
        pair.port_a = a
        pair.port_b = b
        pair.description = self.description_edit.text().strip()
        pair.auto_create = self.auto_create.isChecked()
        return pair

    def validate(self) -> str:
        values = self.values()
        if not is_valid_port(values.port_a) or not is_valid_port(values.port_b):
            return "请输入有效的 COM 端口号，例如 COM5。"
        if values.port_a == values.port_b:
            return "两端不能是同一个端口。"
        if self.config.is_port_used(values.port_a, values.id) or self.config.is_port_used(values.port_b, values.id):
            return "该端口已在其他配置中使用，请换一个。"
        for port in (values.port_a, values.port_b):
            if port in self.busy_ports and port not in self.own_ports:
                return f"{port} 已被系统或驱动占用，请点「推荐空闲端口」或换一个。"
        return ""


class _LoopbackWorker(QObject):
    log = Signal(str)
    done = Signal(object)

    def __init__(self, port_a: str, port_b: str) -> None:
        super().__init__()
        self.port_a = port_a
        self.port_b = port_b

    def run(self) -> None:
        result = run_loopback(self.port_a, self.port_b, on_step=self.log.emit)
        self.done.emit(result)


class LoopbackDialog(QDialog):
    def __init__(self, port_a: str, port_b: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"回环自检 · {port_a} ↔ {port_b}")
        self.setModal(True)
        self.resize(460, 320)
        self._running = True

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.close_btn = QPushButton("关闭")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.reject)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 16)
        root.setSpacing(12)
        label = QLabel("正在两个端口之间互发测试数据 ...")
        label.setObjectName("muted")
        root.addWidget(label)
        root.addWidget(self.output)
        root.addWidget(self.close_btn)

        self.thread = QThread(self)
        self.worker = _LoopbackWorker(port_a, port_b)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self._append)
        self.worker.done.connect(self._finished)
        QTimer.singleShot(0, self.thread.start)

    def _append(self, text: str) -> None:
        self.output.appendPlainText(f"· {text}")

    def _finished(self, result: TestResult) -> None:
        self._running = False
        self.thread.quit()
        self.thread.wait(1000)
        mark = "✓" if result.ok else "!"
        self.output.appendPlainText("")
        self.output.appendPlainText(f"{mark} {result.title}")
        self.output.appendPlainText(result.detail)
        self.close_btn.setEnabled(True)

    def closeEvent(self, event) -> None:
        if self._running:
            event.ignore()
            return
        super().closeEvent(event)


class _DriverInstallWorker(QObject):
    log = Signal(str)
    done = Signal(object)

    def run(self) -> None:
        result = install_com0com(on_step=self.log.emit)
        self.done.emit(result)


class DriverInstallDialog(QDialog):
    installed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("安装 com0com 驱动")
        self.setModal(True)
        self.resize(480, 300)
        self._running = True

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.close_btn = QPushButton("完成")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 16)
        root.setSpacing(12)
        label = QLabel("正在安装官方签名的 com0com 驱动，请在弹出的管理员提示里点「是」。")
        label.setObjectName("muted")
        label.setWordWrap(True)
        root.addWidget(label)
        root.addWidget(self.output)
        root.addWidget(self.close_btn)

        self.thread = QThread(self)
        self.worker = _DriverInstallWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self._append)
        self.worker.done.connect(self._finished)
        QTimer.singleShot(0, self.thread.start)

    def _append(self, text: str) -> None:
        self.output.appendPlainText(f"· {text}")

    def _finished(self, result) -> None:
        self._running = False
        self.thread.quit()
        self.thread.wait(1000)
        mark = "✓" if result.ok else "!"
        self.output.appendPlainText("")
        self.output.appendPlainText(f"{mark} {result.message}")
        self.close_btn.setEnabled(True)
        self.installed.emit(bool(result.ok))

    def closeEvent(self, event) -> None:
        if self._running:
            event.ignore()
            return
        super().closeEvent(event)
