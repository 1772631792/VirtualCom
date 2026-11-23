from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.backend import Com0comBackend
from app.config import ConfigManager
from app.constants import APP_NAME, APP_VERSION
from app.logger import get_logger, setup_logging
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main() -> int:
    setup_logging()
    log = get_logger()
    log.info("启动 %s v%s", APP_NAME, APP_VERSION)

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager()
    apply_theme(app, config.settings.theme)

    backend = Com0comBackend(config)
    window = MainWindow(config, backend)
    if not config.settings.start_minimized:
        window.show()

    def handle_exception(exc_type, exc, tb) -> None:
        log.exception("未捕获异常", exc_info=(exc_type, exc, tb))

    sys.excepthook = handle_exception
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
