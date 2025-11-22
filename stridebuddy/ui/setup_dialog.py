from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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
    QComboBox,
)

from ..storage import load_settings, save_settings, clear_all_saved_passwords, open_settings_folder, list_saved_accounts
from pathlib import Path
from PySide6.QtWidgets import QFileDialog
import json
from ..resources import asset_path
from .. import __version__


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

        # Notifications tab
        self.tab_notifications = QWidget(self)
        self._build_notifications_tab(self.tab_notifications)
        self.tabs.addTab(self.tab_notifications, "Notifications")

        # Chat tab
        self.tab_chat = QWidget(self)
        self._build_chat_tab(self.tab_chat)
        self.tabs.addTab(self.tab_chat, "Chat")

        # Appearance tab
        self.tab_appearance = QWidget(self)
        self._build_appearance_tab(self.tab_appearance)
        self.tabs.addTab(self.tab_appearance, "Appearance")

        # Privacy tab
        self.tab_privacy = QWidget(self)
        self._build_privacy_tab(self.tab_privacy)
        self.tabs.addTab(self.tab_privacy, "Privacy")

        # Data tab
        self.tab_data = QWidget(self)
        self._build_data_tab(self.tab_data)
        self.tabs.addTab(self.tab_data, "Data")

        # About tab
        self.tab_about = QWidget(self)
        self._build_about_tab(self.tab_about)
        self.tabs.addTab(self.tab_about, "About")

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

    def _build_notifications_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        header = QLabel("Notifications")
        header.setStyleSheet("QLabel { font-weight: 700; }")
        layout.addWidget(header)
        self.chk_notif_sounds = QCheckBox("Enable sounds", tab)
        self.chk_notif_sounds.setChecked(bool(self.settings.get("notifications_sounds", True)))
        layout.addWidget(self.chk_notif_sounds)
        self.chk_notif_toasts = QCheckBox("Desktop toasts", tab)
        self.chk_notif_toasts.setChecked(bool(self.settings.get("notifications_toasts", True)))
        layout.addWidget(self.chk_notif_toasts)
        hint = QLabel("Per-buddy mute planned.")
        hint.setStyleSheet("QLabel { color:#666666; }")
        layout.addWidget(hint)

    def _build_chat_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        header = QLabel("Chat")
        header.setStyleSheet("QLabel { font-weight: 700; }")
        layout.addWidget(header)
        self.chk_chat_bold = QCheckBox("Default bold", tab)
        self.chk_chat_bold.setChecked(bool(self.settings.get("chat_default_bold", False)))
        layout.addWidget(self.chk_chat_bold)
        self.chk_chat_italic = QCheckBox("Default italic", tab)
        self.chk_chat_italic.setChecked(bool(self.settings.get("chat_default_italic", False)))
        layout.addWidget(self.chk_chat_italic)
        self.chk_chat_links = QCheckBox("Allow clickable links", tab)
        self.chk_chat_links.setChecked(bool(self.settings.get("chat_allow_links", True)))
        layout.addWidget(self.chk_chat_links)
        self.chk_chat_emoji = QCheckBox("Replace emoji shortcodes", tab)
        self.chk_chat_emoji.setChecked(bool(self.settings.get("chat_emoji_replace", True)))
        layout.addWidget(self.chk_chat_emoji)
        self.chk_chat_logs = QCheckBox("Enable transcript logging", tab)
        self.chk_chat_logs.setChecked(bool(self.settings.get("chat_transcripts_enabled", False)))
        layout.addWidget(self.chk_chat_logs)

    def _build_appearance_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        header = QLabel("Appearance")
        header.setStyleSheet("QLabel { font-weight: 700; }")
        layout.addWidget(header)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        self.cmb_theme = QComboBox(tab)
        self.cmb_theme.addItems(["Light", "Retro", "Auto"])
        self.cmb_theme.setCurrentText(self.settings.get("appearance_theme", "Light"))
        # White text in dropdown list; black when selected
        self.cmb_theme.setStyleSheet(
            "QComboBox { color: black; }"
            "QComboBox QAbstractItemView { color: white; background: #1f2937; }"
        )
        form.addRow(QLabel("Theme:"), self.cmb_theme)
        self.cmb_ts = QComboBox(tab)
        self.cmb_ts.addItems(["12h", "24h"])
        self.cmb_ts.setCurrentText(self.settings.get("appearance_timestamp_format", "12h"))
        self.cmb_ts.setStyleSheet(
            "QComboBox { color: black; }"
            "QComboBox QAbstractItemView { color: white; background: #1f2937; }"
        )
        form.addRow(QLabel("Timestamp:"), self.cmb_ts)
        layout.addLayout(form)
        self.chk_compact = QCheckBox("Compact spacing", tab)
        self.chk_compact.setChecked(bool(self.settings.get("appearance_compact", False)))
        layout.addWidget(self.chk_compact)

    def _build_privacy_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        header = QLabel("Privacy")
        header.setStyleSheet("QLabel { font-weight: 700; }")
        layout.addWidget(header)
        self.chk_buddies_only = QCheckBox("Only allow messages from buddies", tab)
        self.chk_buddies_only.setChecked(bool(self.settings.get("privacy_buddies_only", False)))
        layout.addWidget(self.chk_buddies_only)
        self.chk_warn_confirm = QCheckBox("Confirm before sending 'Warn'", tab)
        self.chk_warn_confirm.setChecked(bool(self.settings.get("privacy_warn_confirm", True)))
        layout.addWidget(self.chk_warn_confirm)

    def _build_data_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        header = QLabel("Data")
        header.setStyleSheet("QLabel { font-weight: 700; }")
        layout.addWidget(header)
        self.btn_open_folder = QPushButton("Open settings folder", tab)
        self.btn_open_folder.clicked.connect(open_settings_folder)
        layout.addWidget(self.btn_open_folder)
        self.btn_export = QPushButton("Export settings...", tab)
        self.btn_export.clicked.connect(self._export_settings)
        layout.addWidget(self.btn_export)
        self.btn_import = QPushButton("Import settings...", tab)
        self.btn_import.clicked.connect(self._import_settings)
        layout.addWidget(self.btn_import)
        saved = list_saved_accounts()
        self.btn_clear_pw = QPushButton(f"Clear saved passwords ({len(saved)} account(s))", tab)
        self.btn_clear_pw.clicked.connect(self._clear_saved_passwords)
        layout.addWidget(self.btn_clear_pw)

    def _build_about_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        # Brand header
        brand_row = QHBoxLayout()
        icon_label = QLabel(tab)
        pix = QPixmap(asset_path("sb_runner.svg"))
        if not pix.isNull():
            icon_label.setPixmap(pix.scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title = QLabel("StrideBuddy")
        title.setStyleSheet("QLabel { font-size: 18px; font-weight: 800; color: #1e73be; }")
        brand_row.addWidget(icon_label)
        brand_row.addWidget(title)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)

        # Tagline and version
        tagline = QLabel("A modern, nostalgic messenger inspired by the classics.")
        layout.addWidget(tagline)
        ver = QLabel(f"Version: {__version__}")
        ver.setStyleSheet("QLabel { color: #666666; }")
        layout.addWidget(ver)

        # Links
        base_url = self.settings.get("server_url", "http://127.0.0.1:5000")
        links = QLabel(f'<a style=\"color:black;\" href=\"{base_url}/help\">Help Center</a>  •  <a style=\"color:black;\" href=\"{base_url}/signup\">Create an account</a>')
        links.setOpenExternalLinks(True)
        layout.addWidget(links)

        # Credits / legal
        fine = QLabel("© 2025 StrideBuddy. For personal and educational use.")
        fine.setStyleSheet("QLabel { color: #777777; font-size: 12px; }")
        layout.addStretch(1)
        layout.addWidget(fine)

    def _on_accept(self) -> None:
        # Persist modified settings
        updated = dict(self.settings)
        updated["last_screen_name"] = self.default_name.text().strip()
        updated["save_password"] = bool(self.chk_save_password.isChecked())
        updated["auto_login"] = bool(self.chk_auto_login.isChecked())
        updated["server_url"] = self.server_url.text().strip() or "http://127.0.0.1:5000"
        updated["notifications_sounds"] = bool(self.chk_notif_sounds.isChecked())
        updated["notifications_toasts"] = bool(self.chk_notif_toasts.isChecked())
        updated["chat_default_bold"] = bool(self.chk_chat_bold.isChecked())
        updated["chat_default_italic"] = bool(self.chk_chat_italic.isChecked())
        updated["chat_allow_links"] = bool(self.chk_chat_links.isChecked())
        updated["chat_emoji_replace"] = bool(self.chk_chat_emoji.isChecked())
        updated["chat_transcripts_enabled"] = bool(self.chk_chat_logs.isChecked())
        updated["appearance_theme"] = self.cmb_theme.currentText()
        updated["appearance_timestamp_format"] = self.cmb_ts.currentText()
        updated["appearance_compact"] = bool(self.chk_compact.isChecked())
        updated["privacy_buddies_only"] = bool(self.chk_buddies_only.isChecked())
        updated["privacy_warn_confirm"] = bool(self.chk_warn_confirm.isChecked())
        save_settings(updated)
        self.accept()

    def _reset_defaults(self) -> None:
        self.default_name.setText("")
        self.chk_save_password.setChecked(False)
        self.chk_auto_login.setChecked(False)
        self.server_url.setText("http://127.0.0.1:5000")
        self.chk_notif_sounds.setChecked(True)
        self.chk_notif_toasts.setChecked(True)
        self.chk_chat_bold.setChecked(False)
        self.chk_chat_italic.setChecked(False)
        self.chk_chat_links.setChecked(True)
        self.chk_chat_emoji.setChecked(True)
        self.chk_chat_logs.setChecked(False)
        self.cmb_theme.setCurrentText("Light")
        self.cmb_ts.setCurrentText("12h")
        self.chk_compact.setChecked(False)
        self.chk_buddies_only.setChecked(False)
        self.chk_warn_confirm.setChecked(True)

    # Data helpers
    def _export_settings(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export settings", "stridebuddy-settings.json", "JSON Files (*.json)")
        if not path:
            return
        data = load_settings()
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _import_settings(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import settings", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            data = json.loads(text)
            save_settings(data)
            # Rehydrate UI
            self.settings = load_settings()
            self.default_name.setText(self.settings.get("last_screen_name", ""))
            self.chk_save_password.setChecked(bool(self.settings.get("save_password")))
            self.chk_auto_login.setChecked(bool(self.settings.get("auto_login")))
            self.server_url.setText(self.settings.get("server_url", "http://127.0.0.1:5000"))
            self.chk_notif_sounds.setChecked(bool(self.settings.get("notifications_sounds")))
            self.chk_notif_toasts.setChecked(bool(self.settings.get("notifications_toasts")))
            self.chk_chat_bold.setChecked(bool(self.settings.get("chat_default_bold")))
            self.chk_chat_italic.setChecked(bool(self.settings.get("chat_default_italic")))
            self.chk_chat_links.setChecked(bool(self.settings.get("chat_allow_links")))
            self.chk_chat_emoji.setChecked(bool(self.settings.get("chat_emoji_replace")))
            self.chk_chat_logs.setChecked(bool(self.settings.get("chat_transcripts_enabled")))
            self.cmb_theme.setCurrentText(self.settings.get("appearance_theme", "Light"))
            self.cmb_ts.setCurrentText(self.settings.get("appearance_timestamp_format", "12h"))
            self.chk_compact.setChecked(bool(self.settings.get("appearance_compact")))
            self.chk_buddies_only.setChecked(bool(self.settings.get("privacy_buddies_only")))
            self.chk_warn_confirm.setChecked(bool(self.settings.get("privacy_warn_confirm", True)))
        except Exception:
            pass

    def _clear_saved_passwords(self) -> None:
        clear_all_saved_passwords()
        self.btn_clear_pw.setText("Clear saved passwords (0 account(s))")


