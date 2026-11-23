from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "plus": "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z",
    "refresh": "M17.65 6.35A8 8 0 1 0 19.74 12h-2.04A6 6 0 1 1 14.4 7.4l-2.4 2.4h6V3.8l-1.73 1.73z",
    "trash": "M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z",
    "settings": "M19.14 12.94a7.5 7.5 0 0 0 .05-.94 7.5 7.5 0 0 0-.05-.94l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.3 7.3 0 0 0-1.63-.94l-.36-2.54a.5.5 0 0 0-.5-.42h-3.84a.5.5 0 0 0-.5.42l-.36 2.54c-.59.24-1.13.56-1.63.94l-2.39-.96a.5.5 0 0 0-.6.22L2.74 8.84a.5.5 0 0 0 .12.64l2.03 1.58c-.03.31-.05.62-.05.94s.02.63.05.94l-2.03 1.58a.5.5 0 0 0-.12.64l1.92 3.32c.13.22.38.31.6.22l2.39-.96c.5.38 1.04.7 1.63.94l.36 2.54c.04.24.25.42.5.42h3.84c.25 0 .46-.18.5-.42l.36-2.54c.59-.24 1.13-.56 1.63-.94l2.39.96c.22.09.47 0 .6-.22l1.92-3.32a.5.5 0 0 0-.12-.64l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z",
    "plug": "M7 2v6h2V2H7zm8 0v6h2V2h-2zM6 9v3c0 3.5 2.4 6.4 5.5 6.9V22h3v-3.1C17.6 18.4 20 15.5 20 12V9h-2v3c0 2.8-1.8 5-4.5 5.4V9h-2v8.4C8.8 17 7 14.8 7 12V9H6z",
    "edit": "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z",
    "check": "M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
    "warn": "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
    "info": "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z",
    "folder": "M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2z",
    "rocket": "M14.06 9.94 9.06 5 4 4l1 5.06 4.94 5 4.12-4.12zM7.5 11.5A5.5 5.5 0 0 1 4.7 20l2.5-2.5.5-2.5 2.5-.5L12.7 12a5.5 5.5 0 0 1-5.2-.5zM17 3a4 4 0 0 0-1.5 7.7l2.3 2.3 1.5-1.5-1.6-1.6A4 4 0 0 0 17 3z",
    "search": "M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 5 1.5-1.5-5-5zm-6 0A4.5 4.5 0 1 1 15.5 9.5 4.5 4.5 0 0 1 9.5 14z",
    "close": "M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    "min": "M5 11h14v2H5z",
    "max": "M5 5h14v14H5V7h12V5H5z",
    "restore": "M7 7h10v10H7V7zm2 2v6h6V9H9zm-4-4h12v2H5V5zm0 14h12v2H5v-2z",
    "chevron": "M8.59 16.59 13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z",
    "save": "M17 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7l-4-4zm-5 16a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm3-10H5V5h10v4z",
}


@lru_cache(maxsize=128)
def pixmap(name: str, color: str = "#DCE7FF", size: int = 20) -> QPixmap:
    path = PATHS.get(name, PATHS["info"])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24"><path fill="{color}" d="{path}"/></svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    result = QPixmap(size, size)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    renderer.render(painter)
    painter.end()
    return result


def icon(name: str, color: str = "#DCE7FF", size: int = 20) -> QIcon:
    return QIcon(pixmap(name, color, size))
