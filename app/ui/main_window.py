from __future__ import annotations

import json
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..backend import BackendStatus, Com0comBackend
from ..config import ConfigManager, config_path
from ..constants import APP_NAME, APP_TITLE, APP_VERSION
from ..logger import get_logger
from ..models import PairConfig
from ..resources import app_icon, logo_path
from ..utils import open_path
from .dialogs import DriverInstallDialog, LoopbackDialog, PairDialog
from .icons import icon
from .theme import THEME_NAMES, apply_theme, palette
from .toast import ToastManager
from .widgets import NavButton, PairCard, StatCard, TitleBar

log = get_logger()


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, backend: Com0comBackend) -> None:
        super().__init__()
        self.config = config
        self.backend = backend
        self.toast = ToastManager(self)
        self._force_quit = False
        self._status = BackendStatus(False, "", False)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.resize(1120, 730)
        self.setMinimumSize(900, 620)
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(app_icon())
        self._center()

        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.titlebar = TitleBar(self, APP_TITLE)
        self.titlebar.minimizeClicked.connect(self.showMinimized)
        self.titlebar.maximizeClicked.connect(self._toggle_maximize)
        self.titlebar.closeClicked.connect(self._close_requested)
        root.addWidget(self.titlebar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        self.stack = QStackedWidget()
        self.pairs_page, self.pairs_widgets = self._build_pairs_page()
        self.settings_page, self.settings_widgets = self._build_settings_page()
        self.help_page = self._build_help_page()
        for page in (self.pairs_page, self.settings_page, self.help_page):
            self.stack.addWidget(page)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        self._init_tray()
        self.refresh()
        if self.config.settings.start_minimized:
            QTimer.singleShot(0, self.hide)
        else:
            QTimer.singleShot(0, self.show)
        if self.config.settings.auto_apply_on_start:
            QTimer.singleShot(400, self._auto_apply)
        if not self._status.available and not self.config.settings.driver_prompt_declined:
            QTimer.singleShot(900, self._prompt_driver_install)

    def _center(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geometry = screen.availableGeometry()
        self.move(
            geometry.center().x() - self.width() // 2,
            geometry.center().y() - self.height() // 2,
        )

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _close_requested(self) -> None:
        if self.config.settings.minimize_to_tray and self.tray.isVisible():
            self.hide()
            self.toast.show("已最小化到系统托盘", "info", 1800)
        else:
            self.close()

    # ---------------- Sidebar ----------------
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(228)

        logo = QLabel()
        pixmap = QPixmap(str(logo_path())).scaled(46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)

        brand = QLabel("VirtualCom")
        brand.setObjectName("brand")
        tagline = QLabel("虚拟串口工作台")
        tagline.setObjectName("muted")

        brand_box = QHBoxLayout()
        brand_box.setContentsMargins(18, 0, 10, 0)
        brand_box.setSpacing(10)
        brand_box.addWidget(logo)
        brand_box.addStretch(1)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addWidget(brand)
        texts.addWidget(tagline)
        brand_box.addLayout(texts)

        self.nav_pairs = NavButton("串口对管理", "plug")
        self.nav_settings = NavButton("系统设置", "settings")
        self.nav_help = NavButton("使用帮助", "info")
        self.nav_pairs.set_active(True)
        self.nav_pairs.clicked.connect(lambda: self._navigate(0))
        self.nav_settings.clicked.connect(lambda: self._navigate(1))
        self.nav_help.clicked.connect(lambda: self._navigate(2))

        nav = QVBoxLayout()
        nav.setSpacing(6)
        nav.setContentsMargins(12, 24, 12, 0)
        nav.addWidget(self.nav_pairs)
        nav.addWidget(self.nav_settings)
        nav.addWidget(self.nav_help)

        self.driver_dot = QLabel("●")
        self.driver_dot.setStyleSheet("color: #F6CF8B; font-size: 11px;")
        self.driver_title = QLabel("驱动状态")
        self.driver_title.setObjectName("section")
        self.driver_detail = QLabel("正在检测 ...")
        self.driver_detail.setObjectName("muted")
        self.driver_detail.setWordWrap(True)
        self.admin_detail = QLabel("")
        self.admin_detail.setObjectName("faint")
        self.admin_detail.setWordWrap(True)

        self.redetect_btn = QPushButton("重新检测驱动")
        self.redetect_btn.setProperty("variant", "ghost")
        self.redetect_btn.setIcon(icon("refresh", "#9AAAD0", 14))
        self.redetect_btn.clicked.connect(self.refresh)

        self.install_driver_btn = QPushButton("一键安装驱动")
        self.install_driver_btn.setProperty("variant", "primary")
        self.install_driver_btn.setIcon(icon("rocket", "#06302D", 14))
        self.install_driver_btn.clicked.connect(self._install_driver_dialog)

        status_inner = QVBoxLayout()
        status_inner.setSpacing(6)
        top = QHBoxLayout()
        top.addWidget(self.driver_dot)
        top.addWidget(self.driver_title)
        top.addStretch(1)
        status_inner.addLayout(top)
        status_inner.addWidget(self.driver_detail)
        status_inner.addWidget(self.admin_detail)
        status_inner.addWidget(self.redetect_btn)
        status_inner.addWidget(self.install_driver_btn)

        status_card = QFrame()
        status_card.setObjectName("card")
        status_card.setLayout(status_inner)

        status_box = QVBoxLayout()
        status_box.setContentsMargins(12, 0, 12, 14)
        status_box.addStretch(1)
        status_box.addWidget(status_card)

        version = QLabel(f"v{APP_VERSION} · 本地配置")
        version.setObjectName("faint")
        version.setAlignment(Qt.AlignCenter)
        status_box.addWidget(version)

        root = QVBoxLayout(side)
        root.setContentsMargins(0, 18, 0, 0)
        root.setSpacing(0)
        root.addLayout(brand_box)
        root.addLayout(nav)
        root.addLayout(status_box, 1)
        return side

    def _navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button in (self.nav_pairs, self.nav_settings, self.nav_help):
            button.set_active(False)
        [self.nav_pairs, self.nav_settings, self.nav_help][index].set_active(True)

    # ---------------- Pairs page ----------------
    def _build_pairs_page(self) -> tuple[QWidget, dict]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        title = QLabel("串口对管理")
        title.setObjectName("title")
        subtitle = QLabel("创建、编辑或删除成对出现的虚拟 COM 端口。配置保存在本地，重启软件不会丢失。")
        subtitle.setObjectName("muted")

        add_btn = QPushButton("新建串口对")
        add_btn.setProperty("variant", "primary")
        add_btn.setIcon(icon("plus", "#06302D", 16))
        add_btn.clicked.connect(self.on_add_pair)
        refresh_btn = QPushButton("刷新")
        refresh_btn.setIcon(icon("refresh", "#9AAAD0", 15))
        refresh_btn.clicked.connect(self.refresh)
        clear_btn = QPushButton("清空配置")
        clear_btn.setProperty("variant", "danger")
        clear_btn.clicked.connect(self.on_clear_all)

        header_actions = QHBoxLayout()
        header_actions.setSpacing(8)
        header_actions.addStretch(1)
        header_actions.addWidget(clear_btn)
        header_actions.addWidget(refresh_btn)
        header_actions.addWidget(add_btn)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addLayout(header_actions)

        self.stat_total = StatCard("配置总数", "0", "#8FC7FF")
        self.stat_ready = StatCard("已就绪", "0", "#7CE0B4")
        self.stat_missing = StatCard("未创建", "0", "#F6CF8B")
        stats = QHBoxLayout()
        stats.setSpacing(12)
        for card in (self.stat_total, self.stat_ready, self.stat_missing):
            stats.addWidget(card)

        self.pair_container = QFrame()
        self.pair_container.setObjectName("pairContainer")
        pair_layout = QVBoxLayout(self.pair_container)
        pair_layout.setContentsMargins(0, 0, 0, 0)
        pair_layout.setSpacing(12)
        pair_layout.setAlignment(Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.pair_container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        footer = QLabel("小提示：点击「自检」可以在两端互发数据，确认虚拟串口真的连通。")
        footer.setObjectName("faint")

        layout.addLayout(header)
        layout.addWidget(subtitle)
        layout.addLayout(stats)
        layout.addWidget(scroll, 1)
        layout.addWidget(footer)
        return page, {"scroll": scroll}

    # ---------------- Settings page ----------------
    def _build_settings_page(self) -> tuple[QWidget, dict]:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(28, 24, 28, 20)
        outer.setSpacing(16)

        title = QLabel("系统设置")
        title.setObjectName("title")
        subtitle = QLabel("驱动路径、外观与启动行为都可以在这里调整，修改后自动保存。")
        subtitle.setObjectName("muted")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(2, 2, 8, 2)
        column.setSpacing(14)

        # 驱动卡片
        driver_card = QFrame()
        driver_card.setObjectName("card")
        d = QVBoxLayout(driver_card)
        d.setContentsMargins(20, 18, 20, 18)
        d.setSpacing(12)
        head = QLabel("com0com 驱动")
        head.setObjectName("section")
        note = QLabel("VirtualCom 使用 com0com 创建真实的 Windows 虚拟串口对。首次使用需要安装驱动并以管理员身份运行。")
        note.setObjectName("muted")
        note.setWordWrap(True)

        row = QHBoxLayout()
        self.setupc_edit = QLineEdit()
        self.setupc_edit.setPlaceholderText("例如：C:\\Program Files (x86)\\com0com\\setupc.exe")
        self.setupc_edit.editingFinished.connect(self._save_setupc_path)
        browse = QPushButton("选择文件")
        browse.setIcon(icon("folder", "#9AAAD0", 15))
        browse.clicked.connect(self._browse_setupc)
        detect = QPushButton("自动检测")
        detect.setIcon(icon("search", "#9AAAD0", 15))
        detect.clicked.connect(self._auto_detect)
        row.addWidget(self.setupc_edit)
        row.addWidget(browse)
        row.addWidget(detect)

        self.settings_install_btn = QPushButton("一键安装 com0com 驱动")
        self.settings_install_btn.setProperty("variant", "primary")
        self.settings_install_btn.setIcon(icon("rocket", "#06302D", 15))
        self.settings_install_btn.clicked.connect(self._install_driver_dialog)

        self.driver_hint = QLabel("")
        self.driver_hint.setObjectName("muted")
        self.driver_hint.setWordWrap(True)
        d.addWidget(head)
        d.addWidget(note)
        d.addLayout(row)
        d.addWidget(self.settings_install_btn)
        d.addWidget(self.driver_hint)
        column.addWidget(driver_card)

        # 偏好卡片
        pref_card = QFrame()
        pref_card.setObjectName("card")
        p = QVBoxLayout(pref_card)
        p.setContentsMargins(20, 18, 20, 18)
        p.setSpacing(12)
        p_head = QLabel("外观与启动")
        p_head.setObjectName("section")

        self.theme_combo = QComboBox()
        for key, label in THEME_NAMES.items():
            self.theme_combo.addItem(label, key)
        self.theme_combo.currentIndexChanged.connect(self._change_theme)

        theme_row = QHBoxLayout()
        theme_label = QLabel("主题风格")
        theme_label.setObjectName("muted")
        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)

        self.start_minimized = QCheckBox("启动时最小化到托盘")
        self.minimize_tray = QCheckBox("关闭窗口时最小化到托盘")
        self.auto_apply = QCheckBox("启动时自动创建已启用的串口对")
        self.notifications = QCheckBox("显示操作提示消息")
        for checkbox in (self.start_minimized, self.minimize_tray, self.auto_apply, self.notifications):
            checkbox.stateChanged.connect(self._save_preferences)

        p.addWidget(p_head)
        p.addLayout(theme_row)
        p.addWidget(self.start_minimized)
        p.addWidget(self.minimize_tray)
        p.addWidget(self.auto_apply)
        p.addWidget(self.notifications)
        column.addWidget(pref_card)

        # 端口范围卡片
        range_card = QFrame()
        range_card.setObjectName("card")
        r = QVBoxLayout(range_card)
        r.setContentsMargins(20, 18, 20, 18)
        r.setSpacing(12)
        r_head = QLabel("推荐端口范围")
        r_head.setObjectName("section")
        r_note = QLabel("「推荐空闲端口」只会在这个范围内挑选号码。")
        r_note.setObjectName("muted")
        range_row = QHBoxLayout()
        self.port_min = QSpinBox()
        self.port_max = QSpinBox()
        self.port_min.setRange(1, 256)
        self.port_max.setRange(1, 256)
        self.port_min.setPrefix("COM")
        self.port_max.setPrefix("COM")
        self.port_min.valueChanged.connect(self._save_port_range)
        self.port_max.valueChanged.connect(self._save_port_range)
        range_row.addWidget(QLabel("从"))
        range_row.addWidget(self.port_min)
        range_row.addWidget(QLabel("到"))
        range_row.addWidget(self.port_max)
        range_row.addStretch(1)
        r.addWidget(r_head)
        r.addWidget(r_note)
        r.addLayout(range_row)
        column.addWidget(range_card)

        # 数据卡片
        data_card = QFrame()
        data_card.setObjectName("card")
        data = QVBoxLayout(data_card)
        data.setContentsMargins(20, 18, 20, 18)
        data.setSpacing(12)
        data_head = QLabel("配置数据")
        data_head.setObjectName("section")
        self.config_path_label = QLabel(str(config_path()))
        self.config_path_label.setObjectName("muted")
        self.config_path_label.setWordWrap(True)

        buttons = QHBoxLayout()
        open_dir = QPushButton("打开配置目录")
        open_dir.setIcon(icon("folder", "#9AAAD0", 15))
        open_dir.clicked.connect(lambda: open_path(config_path().parent))
        export_btn = QPushButton("导出配置")
        export_btn.setIcon(icon("save", "#9AAAD0", 15))
        export_btn.clicked.connect(self._export_config)
        reset_btn = QPushButton("恢复默认设置")
        reset_btn.setProperty("variant", "danger")
        reset_btn.clicked.connect(self._reset_settings)
        buttons.addWidget(open_dir)
        buttons.addWidget(export_btn)
        buttons.addStretch(1)
        buttons.addWidget(reset_btn)
        data.addWidget(data_head)
        data.addWidget(self.config_path_label)
        data.addLayout(buttons)
        column.addWidget(data_card)

        column.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll)
        return page, {
            "scroll": scroll,
            "setupc": self.setupc_edit,
            "theme": self.theme_combo,
        }

    # ---------------- Help page ----------------
    def _build_help_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        title = QLabel("使用帮助")
        title.setObjectName("title")
        subtitle = QLabel("三步开始使用，遇到问题先看这里。")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        steps = [
            ("01", "安装 com0com 驱动", "从 com0com 官方发布页安装带签名的驱动。安装后可在设置里自动检测 setupc.exe。"),
            ("02", "新建一对端口", "点击「新建串口对」，选择两个空闲 COM 号。软件会同时保存配置并写入驱动。"),
            ("03", "连接你的程序", "一端接你的串口工具，另一端接设备模拟器。点击「自检」可验证双向收发。"),
        ]
        for number, heading, body in steps:
            card = QFrame()
            card.setObjectName("helpCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(20, 16, 20, 16)
            row.setSpacing(16)
            badge = QLabel(number)
            badge.setStyleSheet("color: #7BE0D0; font-size:23px; font-weight:700; min-width:42px;")
            texts = QVBoxLayout()
            h = QLabel(heading)
            h.setObjectName("section")
            b = QLabel(body)
            b.setObjectName("muted")
            b.setWordWrap(True)
            texts.addWidget(h)
            texts.addWidget(b)
            row.addWidget(badge)
            row.addLayout(texts, 1)
            layout.addWidget(card)

        warn = QFrame()
        warn.setObjectName("helpCard")
        w = QHBoxLayout(warn)
        w.setContentsMargins(20, 16, 20, 16)
        w.setSpacing(12)
        warn_icon = QLabel()
        warn_icon.setPixmap(icon("warn", "#F6CF8B", 20).pixmap(20, 20))
        w.addWidget(warn_icon)
        note = QLabel("创建 / 删除真实 COM 端口需要管理员权限。如果操作失败，请右键以管理员身份重新打开软件。")
        note.setObjectName("muted")
        note.setWordWrap(True)
        w.addWidget(note, 1)
        layout.addWidget(warn)
        layout.addStretch(1)
        return page

    # ---------------- Tray ----------------
    def _init_tray(self) -> None:
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(APP_NAME)
        menu = self.tray.contextMenu() or QMenu(self)
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self._show_window)
        quit_action = QAction("退出 VirtualCom", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self._show_window() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._force_quit = True
        self.close()

    def closeEvent(self, event) -> None:
        if not self._force_quit and self.config.settings.minimize_to_tray and self.tray.isVisible():
            event.ignore()
            self.hide()
            return
        self.tray.hide()
        super().closeEvent(event)

    # ---------------- Refresh ----------------
    def refresh(self) -> None:
        self.backend.refresh_path()
        self._status = self.backend.status()
        self._update_driver_ui()
        self._render_pairs()
        self._sync_settings_ui()

    def _update_driver_ui(self) -> None:
        status = self._status
        self.install_driver_btn.setVisible(not status.available)
        self.settings_install_btn.setVisible(not status.available)
        if status.available:
            color = "#7CE0B4" if status.admin else "#F6CF8B"
            self.driver_dot.setStyleSheet(f"color: {color}; font-size: 11px;")
            self.driver_detail.setText(f"com0com 已就绪 · {len(status.pairs)} 个端口对")
            self.admin_detail.setText("管理员权限：已获取" if status.admin else "管理员权限：未获取（创建会失败）")
            self.driver_hint.setText(f"当前驱动路径：{status.setupc_path}")
        else:
            self.driver_dot.setStyleSheet("color: #F497A6; font-size: 11px;")
            self.driver_detail.setText("未检测到 com0com 驱动")
            self.admin_detail.setText(
                "管理员权限：已获取" if status.admin else "管理员权限：未获取"
            )
            self.driver_hint.setText(status.message or "请在上方选择 setupc.exe，或先安装 com0com。")

    def _driver_pair_for(self, pair: PairConfig):
        return self.backend.find_driver_pair(pair, self._status.pairs)

    def _pair_status(self, pair: PairConfig) -> str:
        if not self._driver_pair_for(pair):
            return "missing"
        return "ready"

    def _render_pairs(self) -> None:
        layout = self.pair_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        pairs = self.config.pairs
        statuses = [self._pair_status(p) for p in pairs]
        self.stat_total.set_value(len(pairs))
        self.stat_ready.set_value(statuses.count("ready"))
        self.stat_missing.set_value(statuses.count("missing"))

        if not pairs:
            empty = QFrame()
            empty.setObjectName("card")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setAlignment(Qt.AlignCenter)
            empty_layout.setSpacing(10)
            empty_icon = QLabel()
            empty_icon.setPixmap(icon("plug", "#7BE0D0", 42).pixmap(42, 42))
            empty_layout.addWidget(empty_icon)
            label = QLabel("还没有任何串口对")
            label.setObjectName("section")
            hint = QLabel("点击右上角「新建串口对」，开始配置你的第一组 COM 端口。")
            hint.setObjectName("muted")
            empty_layout.addWidget(label)
            empty_layout.addWidget(hint)
            layout.addWidget(empty)
            return

        for pair, status in zip(pairs, statuses):
            card = PairCard(
                pair.id,
                pair.name,
                pair.port_a,
                pair.port_b,
                pair.description,
                pair.created_at,
                status,
            )
            card.editRequested.connect(self.on_edit_pair)
            card.testRequested.connect(self.on_test_pair)
            card.deleteRequested.connect(self.on_delete_pair)
            card.createRequested.connect(self.on_create_pair)
            layout.addWidget(card)

    # ---------------- Pair actions ----------------
    def on_add_pair(self) -> None:
        dialog = PairDialog(self.config, None, self, backend=self.backend)
        if dialog.exec() != QDialog.Accepted:
            return
        error = dialog.validate()
        if error:
            QMessageBox.warning(self, "输入有误", error)
            return
        pair = dialog.values()
        if not self.config.add_pair(pair):
            self.toast.show("保存配置失败", "warn")
            return
        self.refresh()
        if pair.auto_create:
            self._install(pair)
        else:
            self.toast.show("已保存配置，可稍后点击卡片上的「创建」", "ok")

    def on_edit_pair(self, pair_id: str) -> None:
        pair = self.config.find_pair(pair_id)
        if not pair:
            return
        dialog = PairDialog(self.config, pair, self, backend=self.backend)
        if dialog.exec() != QDialog.Accepted:
            return
        error = dialog.validate()
        if error:
            QMessageBox.warning(self, "输入有误", error)
            return
        updated = dialog.values()
        ports_changed = (updated.port_a, updated.port_b) != (pair.port_a, pair.port_b)
        had_driver = self._driver_pair_for(pair) is not None

        if ports_changed and had_driver:
            answer = QMessageBox.question(
                self,
                "端口已变更",
                "修改端口需要重建驱动中的串口对。是否继续？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            self.backend.remove(pair)

        self.config.update_pair(updated)
        self.refresh()
        updated = self.config.find_pair(pair_id) or updated
        if updated.auto_create and (ports_changed or not self._driver_pair_for(updated)):
            self._install(updated)
        else:
            self.toast.show("配置已更新", "ok")

    def on_create_pair(self, pair_id: str) -> None:
        pair = self.config.find_pair(pair_id)
        if pair:
            self._install(pair)

    def _install(self, pair: PairConfig) -> None:
        result = self.backend.install(pair)
        if result.ok:
            if result.driver_pair:
                pair.driver_id = result.driver_pair.id
        self.refresh()
        self.toast.show(result.message or ("已创建" if result.ok else "创建失败"), "ok" if result.ok else "warn")

    def on_delete_pair(self, pair_id: str) -> None:
        pair = self.config.find_pair(pair_id)
        if not pair:
            return
        box = QMessageBox(self)
        box.setWindowTitle("删除串口对")
        box.setText(f"确定删除 {pair.port_a} ↔ {pair.port_b} 吗？")
        box.setInformativeText(
            "本地配置一定会被删除；也可以同时移除系统中的虚拟端口。"
            "这不会卸载 com0com 驱动本身。"
        )
        with_driver = box.addButton("删除配置并移除虚拟端口", QMessageBox.DestructiveRole)
        config_only = box.addButton("仅删除配置", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked not in (with_driver, config_only):
            return

        if clicked is with_driver:
            result = self.backend.remove(pair)
            if not result.ok:
                self.toast.show(result.message, "warn")
                return
        self.config.remove_pair(pair_id)
        self.refresh()
        self.toast.show("已删除串口对配置", "ok")

    def on_clear_all(self) -> None:
        if not self.config.pairs:
            self.toast.show("当前没有配置", "info")
            return
        answer = QMessageBox.question(
            self,
            "清空全部配置",
            f"确定删除全部 {len(self.config.pairs)} 条配置吗？驱动中的端口不会受影响。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.config.clear_pairs()
        self.refresh()
        self.toast.show("全部配置已清空", "ok")

    def on_test_pair(self, pair_id: str) -> None:
        pair = self.config.find_pair(pair_id)
        if not pair:
            return
        dialog = LoopbackDialog(pair.port_a, pair.port_b, self)
        dialog.exec()

    def _auto_apply(self) -> None:
        created = 0
        for pair in list(self.config.pairs):
            if pair.auto_create and not self._driver_pair_for(pair):
                result = self.backend.install(pair)
                if result.ok and result.driver_pair:
                    pair.driver_id = result.driver_pair.id
                    self.config.save()
                    created += 1
        self.refresh()
        if created:
            self.toast.show(f"已自动创建 {created} 个串口对", "ok")

    def _prompt_driver_install(self) -> None:
        if self._status.available:
            return
        box = QMessageBox(self)
        box.setWindowTitle("还没有检测到虚拟串口驱动")
        box.setText("VirtualCom 需要 com0com 才能创建真实的 COM 端口。")
        box.setInformativeText("软件里已经内置了官方签名安装包，点击「一键安装驱动」即可自动安装。")
        install_btn = box.addButton("一键安装驱动", QMessageBox.AcceptRole)
        box.addButton("以后再说", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is install_btn:
            self._install_driver_dialog()
        else:
            self.config.update_settings(driver_prompt_declined=True)

    def _install_driver_dialog(self) -> None:
        dialog = DriverInstallDialog(self)
        dialog.installed.connect(self._after_driver_install)
        dialog.exec()

    def _after_driver_install(self, ok: bool) -> None:
        self.config.update_settings(driver_prompt_declined=True)
        self.refresh()
        if ok:
            self.toast.show("驱动已就绪，正在创建已有配置 ...", "ok")
            QTimer.singleShot(300, self._auto_apply)
        else:
            self.toast.show("驱动安装未完成，请查看安装窗口里的提示", "warn")

    # ---------------- Settings actions ----------------
    def _sync_settings_ui(self) -> None:
        s = self.config.settings
        self.setupc_edit.setText(self.backend.setupc_path)
        keys = list(THEME_NAMES.keys())
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(keys.index(s.theme) if s.theme in keys else 0)
        self.theme_combo.blockSignals(False)
        for checkbox, value in [
            (self.start_minimized, s.start_minimized),
            (self.minimize_tray, s.minimize_to_tray),
            (self.auto_apply, s.auto_apply_on_start),
            (self.notifications, s.show_notifications),
        ]:
            checkbox.blockSignals(True)
            checkbox.setChecked(value)
            checkbox.blockSignals(False)
        self.port_min.blockSignals(True)
        self.port_max.blockSignals(True)
        self.port_min.setValue(s.port_min)
        self.port_max.setValue(s.port_max)
        self.port_min.blockSignals(False)
        self.port_max.blockSignals(False)

    def _save_setupc_path(self) -> None:
        path = self.setupc_edit.text().strip()
        self.config.update_settings(setupc_path=path)
        self.refresh()

    def _browse_setupc(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 setupc.exe", "", "setupc executable (setupc.exe);;All files (*.*)"
        )
        if not path:
            return
        self.setupc_edit.setText(path)
        self.config.update_settings(setupc_path=path)
        self.refresh()
        self.toast.show("驱动路径已更新", "ok")

    def _auto_detect(self) -> None:
        found = self.backend.autodetect()
        if found and Path(found).is_file():
            self.config.update_settings(setupc_path=found)
            self.toast.show("已找到 setupc.exe", "ok")
        else:
            self.toast.show("没有找到 com0com，请手动选择路径", "warn")
        self.refresh()

    def _change_theme(self) -> None:
        key = self.theme_combo.currentData()
        if not key:
            return
        self.config.update_settings(theme=key)
        apply_theme(QApplication.instance(), key)

    def _save_preferences(self) -> None:
        self.config.update_settings(
            start_minimized=self.start_minimized.isChecked(),
            minimize_to_tray=self.minimize_tray.isChecked(),
            auto_apply_on_start=self.auto_apply.isChecked(),
            show_notifications=self.notifications.isChecked(),
        )

    def _save_port_range(self) -> None:
        low, high = self.port_min.value(), self.port_max.value()
        if low > high:
            return
        self.config.update_settings(port_min=low, port_max=high)

    def _export_config(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "virtualcom-config.json", "JSON files (*.json)"
        )
        if not target:
            return
        try:
            shutil.copy2(config_path(), target)
            self.toast.show("配置已导出", "ok")
        except Exception as exc:
            QMessageBox.warning(self, "导出失败", str(exc))

    def _reset_settings(self) -> None:
        answer = QMessageBox.question(
            self,
            "恢复默认设置",
            "只会恢复界面与启动设置，串口对配置会保留。是否继续？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.config.reset_settings()
        self.refresh()
        apply_theme(QApplication.instance(), self.config.settings.theme)
        self.toast.show("设置已恢复默认", "ok")
