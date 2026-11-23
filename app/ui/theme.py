from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

PALETTES: dict[str, dict[str, str]] = {
    "midnight": {
        "window": "#0D1226",
        "sidebar": "#111A33",
        "titlebar": "#10182F",
        "surface": "#17213E",
        "surface_alt": "#1D2949",
        "surface_hover": "#243358",
        "border": "#2B3A63",
        "text": "#EEF3FF",
        "text_dim": "#9AAAD0",
        "text_faint": "#6E80A9",
        "accent": "#7BE0D0",
        "accent_deep": "#2FAE9F",
        "accent_text": "#062B2B",
        "pink": "#EFACC6",
        "success": "#7CE0B4",
        "warning": "#F6CF8B",
        "danger": "#F497A6",
        "input": "#121C37",
        "shadow": "#050916",
        "overlay": "#0A1024",
    },
    "cloud": {
        "window": "#F3F6FC",
        "sidebar": "#E8EDF8",
        "titlebar": "#F7F9FE",
        "surface": "#FFFFFF",
        "surface_alt": "#F6F8FD",
        "surface_hover": "#EAF0FB",
        "border": "#DCE4F2",
        "text": "#23304F",
        "text_dim": "#667599",
        "text_faint": "#9AA7C2",
        "accent": "#2FAE9F",
        "accent_deep": "#248C80",
        "accent_text": "#FFFFFF",
        "pink": "#D9769C",
        "success": "#2E9E78",
        "warning": "#C98A2E",
        "danger": "#D7657B",
        "input": "#FFFFFF",
        "shadow": "#C9D4E8",
        "overlay": "#E7ECF6",
    },
}

THEME_NAMES = {"midnight": "午夜蓝", "cloud": "云雾白"}


def palette(theme: str) -> dict[str, str]:
    return PALETTES.get(theme, PALETTES["midnight"])


def stylesheet(theme: str = "midnight") -> str:
    p = palette(theme)
    return """
    QWidget {{
        background: {window};
        color: {text};
        font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
        font-size: 13px;
    }}
    QFrame#titlebar {{ background: {titlebar}; border: none; }}
    QFrame#sidebar {{ background: {sidebar}; border: none; }}
    QFrame#card, QFrame#pairCard, QFrame#statCard, QFrame#helpCard {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 16px;
    }}
    QFrame#divider {{ background: {border}; max-height: 1px; border: none; }}

    QLabel#title {{ font-size: 25px; font-weight: 700; letter-spacing: 0.4px; }}
    QLabel#section {{ font-size: 15px; font-weight: 600; }}
    QLabel#subtitle, QLabel#muted {{ color: {text_dim}; font-size: 12px; }}
    QLabel#faint {{ color: {text_faint}; font-size: 11px; }}
    QLabel#badge {{
        background: {surface_alt};
        color: {text_dim};
        border: 1px solid {border};
        border-radius: 9px;
        padding: 3px 9px;
        font-size: 11px;
    }}
    QLabel#brand {{ font-size: 18px; font-weight: 700; letter-spacing: 0.6px; }}

    QPushButton {{
        background: {surface_alt};
        color: {text};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 8px 14px;
        min-height: 20px;
    }}
    QPushButton:hover {{ background: {surface_hover}; border-color: {accent_deep}; }}
    QPushButton:pressed {{ background: {surface}; }}
    QPushButton:disabled {{ color: {text_faint}; background: {surface}; border-color: {border}; }}
    QPushButton[variant="primary"] {{
        background: {accent};
        color: {accent_text};
        border: 1px solid {accent};
        font-weight: 700;
    }}
    QPushButton[variant="primary"]:hover {{ background: {accent_deep}; border-color: {accent_deep}; }}
    QPushButton[variant="ghost"] {{ background: transparent; border-color: transparent; color: {text_dim}; }}
    QPushButton[variant="ghost"]:hover {{ background: {surface_alt}; color: {text}; }}
    QPushButton[variant="danger"] {{ color: {danger}; border-color: transparent; background: transparent; }}
    QPushButton[variant="danger"]:hover {{ background: {surface_alt}; border-color: {danger}; }}
    QPushButton[variant="icon"] {{ padding: 0; border: none; background: transparent; }}
    QPushButton[variant="icon"]:hover {{ background: {surface_hover}; border-radius: 8px; }}

    NavButton {{
        background: transparent;
        border: none;
        border-radius: 12px;
        padding: 11px 14px;
        color: {text_dim};
        text-align: left;
        font-size: 13px;
    }}
    NavButton:hover {{ background: {surface_alt}; color: {text}; }}
    NavButton[active="true"] {{ background: {surface_alt}; color: {accent}; font-weight: 700; }}
    NavButton[active="true"]::after {{ border-left: 3px solid {accent}; }}

    QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
        background: {input};
        color: {text};
        border: 1px solid {border};
        border-radius: 9px;
        padding: 7px 10px;
        selection-background-color: {accent_deep};
        min-height: 20px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {accent};
    }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{
        background: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        selection-background-color: {surface_hover};
        padding: 4px;
    }}
    QCheckBox {{ spacing: 8px; color: {text}; }}
    QCheckBox::indicator {{
        width: 17px; height: 17px; border-radius: 5px;
        border: 1px solid {border}; background: {input};
    }}
    QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 9px; margin: 4px 0; }}
    QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 32px; }}
    QScrollBar::handle:vertical:hover {{ background: {text_faint}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 8px; }}
    QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; }}

    QToolTip {{
        background: {overlay};
        color: {text};
        border: 1px solid {border};
        border-radius: 7px;
        padding: 5px 8px;
    }}
    QMessageBox {{ background: {surface}; }}
    QMessageBox QLabel {{ color: {text}; }}
    QProgressBar {{
        background: {input}; border: 1px solid {border}; border-radius: 6px;
        text-align: center; height: 10px;
    }}
    QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}
    QLabel#toastInfo, QLabel#toastOk, QLabel#toastWarn {{
        background: {overlay};
        color: {text};
        border: 1px solid {border};
        border-radius: 11px;
        padding: 10px 15px;
        font-size: 12px;
    }}
    QLabel#toastOk {{ border-color: {success}; }}
    QLabel#toastWarn {{ border-color: {danger}; }}
    """.format(**p)


def apply_theme(app: QApplication, theme: str) -> None:
    app.setStyleSheet(stylesheet(theme))
    p = palette(theme)
    qt_palette = QPalette()
    qt_palette.setColor(QPalette.Window, QColor(p["window"]))
    qt_palette.setColor(QPalette.WindowText, QColor(p["text"]))
    qt_palette.setColor(QPalette.Base, QColor(p["input"]))
    qt_palette.setColor(QPalette.Text, QColor(p["text"]))
    qt_palette.setColor(QPalette.Button, QColor(p["surface"]))
    qt_palette.setColor(QPalette.ButtonText, QColor(p["text"]))
    qt_palette.setColor(QPalette.PlaceholderText, QColor(p["text_faint"]))
    app.setPalette(qt_palette)
