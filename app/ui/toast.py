from __future__ import annotations

from PySide6.QtCore import QObject, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


class ToastManager(QObject):
    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.host = host
        self._active: list[QLabel] = []

    def show(self, text: str, kind: str = "info", duration: int = 2600) -> None:
        label = QLabel(text, self.host)
        object_name = {"ok": "toastOk", "warn": "toastWarn"}.get(kind, "toastInfo")
        label.setObjectName(object_name)
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        label.adjustSize()

        effect = QGraphicsOpacityEffect(label)
        effect.setOpacity(0.0)
        label.setGraphicsEffect(effect)

        x = (self.host.width() - label.width()) // 2
        y = self.host.height() - label.height() - 28
        label.move(max(12, x), max(12, y))
        label.show()
        label.raise_()
        self._active.append(label)

        fade_in = QPropertyAnimation(effect, b"opacity", label)
        fade_in.setDuration(180)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.start()

        QTimer.singleShot(max(600, duration), lambda: self._fade_out(label, effect))

    def _fade_out(self, label: QLabel, effect: QGraphicsOpacityEffect) -> None:
        if label not in self._active:
            return
        animation = QPropertyAnimation(effect, b"opacity", label)
        animation.setDuration(260)
        animation.setStartValue(effect.opacity())
        animation.setEndValue(0.0)
        animation.finished.connect(lambda: self._cleanup(label))
        animation.start()

    def _cleanup(self, label: QLabel) -> None:
        if label in self._active:
            self._active.remove(label)
        label.deleteLater()
