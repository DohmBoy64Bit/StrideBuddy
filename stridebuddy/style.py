from __future__ import annotations

from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import QApplication


def apply_stridebuddy_style(app: QApplication) -> None:
    """Apply a compact, Windows-XP-ish palette, spacing, and fonts."""
    # Font: Tahoma was common on XP/AIM era
    base_font = QFont("Tahoma", 9)
    app.setFont(base_font)

    # Palette tuned for a light, slightly grey UI with blue accents.
    palette = QPalette()
    white = QColor("#ffffff")
    window_bg = QColor("#f1f1f1")
    text_color = QColor("#000000")
    disabled_text = QColor("#808080")
    mid_shadow = QColor("#c8c8c8")
    accent_blue = QColor("#1e73be")

    palette.setColor(QPalette.Window, window_bg)
    palette.setColor(QPalette.Base, white)
    palette.setColor(QPalette.AlternateBase, QColor("#f8f8f8"))
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)
    palette.setColor(QPalette.Button, white)
    palette.setColor(QPalette.Mid, mid_shadow)
    palette.setColor(QPalette.Highlight, accent_blue)
    palette.setColor(QPalette.HighlightedText, white)
    app.setPalette(palette)

    # Compact widget metrics
    app.setStyleSheet(
        """
        QWidget { 
            letter-spacing: 0px; 
        }
        QGroupBox {
            margin-top: 8px;
        }
        QLabel.link {
            color: #1e73be;
        }
        QLabel.muted {
            color: #666666;
        }
        QLineEdit, QComboBox {
            padding: 2px 4px;
        }
        QPushButton {
            padding: 4px 10px;
        }
        """
    )


