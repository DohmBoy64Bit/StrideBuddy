from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from .style import apply_stridebuddy_style
from .ui.sign_on import SignOnWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_stridebuddy_style(app)

    window = SignOnWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


