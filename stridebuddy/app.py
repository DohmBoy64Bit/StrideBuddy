from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from PySide6.QtGui import QIcon

from .style import apply_stridebuddy_style
from .ui.sign_on import SignOnWindow
from .resources import asset_path
from .storage import load_settings


def main() -> None:
    app = QApplication(sys.argv)
    settings = load_settings()
    apply_stridebuddy_style(app, settings)

    # Create a tray icon for notifications (store on app instance)
    tray = QSystemTrayIcon(QIcon(asset_path("sb_runner.svg")), app)
    tray.setToolTip("StrideBuddy")
    tray.show()
    app.setProperty("sb_tray", tray)

    window = SignOnWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


