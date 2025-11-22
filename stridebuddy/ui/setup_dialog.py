from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QHBoxLayout,
)

from ..storage import load_settings, save_settings


class SetupDialog(QDialog):
    """Preferences dialog with basic tabs. Starts with Account and Connection."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("StrideBuddy Setup")
        self.setMinimumWidth(380)
        # Ensure text is readable
        self.setStyleSheet("QLabel { color: #000000; } QCheckBox { color: #000000; }")

        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        # Ensure tab labels are visible on dark/light themes
        self.tabs.setStyleSheet("QTabBar::tab { color: #000000; } QTabBar::tab:selected { color: #000000; }")
        root.addWidget(self.tabs)

        # Load current settings
        self.settings = load_settings()

        # Account tab
        self.tab_account = QWidget(self)
        self._build_account_tab(self.tab_account)
        self.tabs.addTab(self.tab_account, "Account")

        # Connection tab
        self.tab_connection = QWidget(self)
        self._build_connection_tab(self.tab_connection)
        self.tabs.addTab(self.tab_connection, "Connection")

        # Dialog buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        buttons_row = QHBoxLayout()
        self.reset_btn = QPushButton("Reset to defaults", self)
        self.reset_btn.clicked.connect(self._reset_defaults)
        buttons_row.addWidget(self.reset_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(self.buttons)
        root.addLayout(buttons_row)

    def _build_account_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        header = QLabel("Account")
        header.setStyleSheet("QLabel { font-weight: 700; }")
        layout.addWidget(header)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)

        self.default_name = QLineEdit(tab)
        self.default_name.setText(self.settings.get("last_screen_name", ""))
        form.addRow(QLabel("Default screen name:"), self.default_name)
        layout.addLayout(form)

        self.chk_save_password = QCheckBox("Save password", tab)
        self.chk_save_password.setChecked(bool(self.settings.get("save_password", False)))
        layout.addWidget(self.chk_save_password)

        self.chk_auto_login = QCheckBox("Auto-login", tab)
        self.chk_auto_login.setChecked(bool(self.settings.get("auto_login", False)))
        layout.addWidget(self.chk_auto_login)

    def _build_connection_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        header = QLabel("Connection")
        header.setStyleSheet("QLabel { font-weight: 700; }")
        layout.addWidget(header)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)

        self.server_url = QLineEdit(tab)
        self.server_url.setPlaceholderText("http://127.0.0.1:5000")
        self.server_url.setText(self.settings.get("server_url", "http://127.0.0.1:5000"))
        form.addRow(QLabel("Server URL:"), self.server_url)
        layout.addLayout(form)

    def _on_accept(self) -> None:
        # Persist modified settings
        updated = dict(self.settings)
        updated["last_screen_name"] = self.default_name.text().strip()
        updated["save_password"] = bool(self.chk_save_password.isChecked())
        updated["auto_login"] = bool(self.chk_auto_login.isChecked())
        updated["server_url"] = self.server_url.text().strip() or "http://127.0.0.1:5000"
        save_settings(updated)
        self.accept()

    def _reset_defaults(self) -> None:
        self.default_name.setText("")
        self.chk_save_password.setChecked(False)
        self.chk_auto_login.setChecked(False)
        self.server_url.setText("http://127.0.0.1:5000")


