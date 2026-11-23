from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..resources import app_icon
from .icons import icon
from .theme import palette


class NavButton(QPushButton):
    def __init__(self, text: str, icon_name: str) -> None:
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(icon(icon_name, "#7BE0D0", 18))
        self.setIconSize(self.iconSize())

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", accent: str = "#7BE0D0") -> None:
        super().__init__()
        self.setObjectName("statCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._value = QLabel(value)
        self._value.setObjectName("title")
        self._value.setStyleSheet(f"color: {accent};")
        caption = QLabel(title)
        caption.setObjectName("muted")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(3)
        layout.addWidget(self._value)
        layout.addWidget(caption)

    def set_value(self, value: object) -> None:
        self._value.setText(str(value))


class PairCard(QFrame):
    editRequested = Signal(str)
    testRequested = Signal(str)
    deleteRequested = Signal(str)
    createRequested = Signal(str)

    STATUS_STYLE = {
        "ready": ("已就绪", "#7CE0B4", "rgba(124,224,180,0.13)"),
        "missing": ("未创建", "#F6CF8B", "rgba(246,207,139,0.13)"),
        "error": ("异常", "#F497A6", "rgba(244,151,166,0.13)"),
    }

    def __init__(self, pair_id: str, name: str, port_a: str, port_b: str,
                 description: str, created_at: str, status: str = "missing") -> None:
        super().__init__()
        self.pair_id = pair_id
        self.setObjectName("pairCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.name_label = QLabel(name or "未命名串口对")
        self.name_label.setObjectName("section")
        self.name_label.setStyleSheet("font-size:14px; font-weight:700;")

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumWidth(66)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.name_label)
        top.addStretch(1)
        top.addWidget(self.status_label)

        port_row = QHBoxLayout()
        port_row.setSpacing(8)
        self.port_a = self._port_pill(port_a)
        self.port_b = self._port_pill(port_b)
        arrow = QLabel("↔")
        arrow.setObjectName("muted")
        arrow.setStyleSheet("font-size:17px; padding:0 2px;")
        port_row.addWidget(self.port_a)
        port_row.addWidget(arrow)
        port_row.addWidget(self.port_b)
        port_row.addStretch(1)

        desc = QLabel(description or "暂无备注")
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        if not description:
            desc.setStyleSheet("color: #6E80A9;")

        meta = QLabel(f"创建于 {created_at}")
        meta.setObjectName("faint")

        self.edit_btn = self._action_btn("edit", "编辑")
        self.test_btn = self._action_btn("plug", "自检")
        self.create_btn = self._action_btn("refresh", "创建")
        self.delete_btn = self._action_btn("trash", "删除")
        self.delete_btn.setProperty("variant", "danger")

        actions = QHBoxLayout()
        actions.setSpacing(2)
        actions.addStretch(1)
        actions.addWidget(self.create_btn)
        actions.addWidget(self.edit_btn)
        actions.addWidget(self.test_btn)
        actions.addWidget(self.delete_btn)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.addWidget(meta)
        bottom.addStretch(1)
        bottom.addLayout(actions)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 15, 18, 13)
        root.setSpacing(9)
        root.addLayout(top)
        root.addLayout(port_row)
        root.addWidget(desc)
        root.addLayout(bottom)

        self.edit_btn.clicked.connect(lambda: self.editRequested.emit(self.pair_id))
        self.test_btn.clicked.connect(lambda: self.testRequested.emit(self.pair_id))
        self.delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self.pair_id))
        self.create_btn.clicked.connect(lambda: self.createRequested.emit(self.pair_id))
        self.set_status(status)

    def _port_pill(self, text: str) -> QLabel:
        label = QLabel(text or "COM?")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumWidth(82)
        label.setStyleSheet(
            "background: rgba(123,224,208,0.11); color: #9BEBDD; "
            "border: 1px solid rgba(123,224,208,0.28); border-radius: 8px; "
            "padding: 4px 8px; font-weight: 700;"
        )
        return label

    def _action_btn(self, icon_name: str, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("variant", "ghost")
        button.setCursor(Qt.PointingHandCursor)
        button.setIcon(icon(icon_name, "#9AAAD0", 15))
        button.setIconSize(button.iconSize())
        return button

    def set_status(self, status: str) -> None:
        text, color, bg = self.STATUS_STYLE.get(status, self.STATUS_STYLE["missing"])
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {color}; background: {bg}; border: 1px solid {color}55; "
            f"border-radius: 9px; padding: 3px 8px; font-size: 11px; font-weight: 600;"
        )
        self.create_btn.setVisible(status != "ready")
        self.test_btn.setEnabled(status == "ready")


class TitleBar(QFrame):
    minimizeClicked = Signal()
    maximizeClicked = Signal()
    closeClicked = Signal()

    def __init__(self, parent: QWidget, title: str) -> None:
        super().__init__(parent)
        self.setObjectName("titlebar")
        self.setFixedHeight(44)
        self._drag_pos: QPoint | None = None

        label = QLabel(title)
        label.setStyleSheet("font-size:12px; font-weight:600; letter-spacing:0.3px;")

        self.min_btn = QPushButton()
        self.max_btn = QPushButton()
        self.close_btn = QPushButton()
        for btn, name, tip in [
            (self.min_btn, "min", "最小化"),
            (self.max_btn, "max", "最大化 / 还原"),
            (self.close_btn, "close", "关闭"),
        ]:
            btn.setProperty("variant", "icon")
            btn.setFixedSize(40, 40)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setIcon(icon(name, "#9AAAD0", 15))
        self.close_btn.setIcon(icon("close", "#F497A6", 16))

        title_icon = QLabel()
        title_icon.setPixmap(app_icon().pixmap(17, 17))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 6, 0)
        layout.setSpacing(2)
        layout.addWidget(title_icon)
        layout.addSpacing(7)
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

        self.min_btn.clicked.connect(self.minimizeClicked.emit)
        self.max_btn.clicked.connect(self.maximizeClicked.emit)
        self.close_btn.clicked.connect(self.closeClicked.emit)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.maximizeClicked.emit()
        super().mouseDoubleClickEvent(event)


def accent_color(theme: str) -> str:
    return palette(theme)["accent"]
