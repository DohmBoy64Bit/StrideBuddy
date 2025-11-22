from __future__ import annotations

from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import QApplication


def apply_stridebuddy_style(app: QApplication, settings: dict | None = None) -> None:
    """Apply palette, spacing, and fonts based on settings."""
    settings = settings or {}

    # Font
    base_font = QFont("Tahoma", 9 if not settings.get("appearance_font_size") else int(settings["appearance_font_size"]))
    app.setFont(base_font)

    # Theme
    theme = (settings.get("appearance_theme") or "Light").lower()
    palette = QPalette()
    white = QColor("#ffffff")
    text_color = QColor("#000000")
    disabled_text = QColor("#808080")
    mid_shadow = QColor("#c8c8c8")
    if theme == "retro":
        window_bg = QColor("#f3f0e6")  # warm beige
        alt_base = QColor("#f8f4ec")
        accent = QColor("#1e73be")
    else:
        window_bg = QColor("#f1f1f1")
        alt_base = QColor("#f8f8f8")
        accent = QColor("#1e73be")

    palette.setColor(QPalette.Window, window_bg)
    palette.setColor(QPalette.Base, white)
    palette.setColor(QPalette.AlternateBase, alt_base)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)
    palette.setColor(QPalette.Button, white)
    palette.setColor(QPalette.Mid, mid_shadow)
    palette.setColor(QPalette.Highlight, accent)
    palette.setColor(QPalette.HighlightedText, white)
    app.setPalette(palette)

    # Compact spacing
    compact = bool(settings.get("appearance_compact", False))
    pad_ctrl = "2px 4px" if compact else "4px 6px"
    pad_btn = "3px 8px" if compact else "4px 10px"
    app.setStyleSheet(
        f"""
        QWidget {{
            letter-spacing: 0px;
        }}
        QGroupBox {{
            margin-top: 8px;
        }}
        QLabel.link {{
            color: #1e73be;
        }}
        QLabel.muted {{
            color: #666666;
        }}
        QLineEdit, QComboBox {{
            padding: {pad_ctrl};
        }}
        QPushButton {{
            padding: {pad_btn};
        }}
        QTabBar::tab {{
            color: #000000;
        }}
        """
    )


