from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal, QRect, QTimer
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QFrame,
    QSpacerItem,
    QSizePolicy,
    QMainWindow,
    QDialog,
    QApplication,
)

from .. import __app_name__, __version__
from ..resources import asset_path
from .buddy_list import BuddyListWindow
from .setup_dialog import SetupDialog
import webbrowser
import requests
from ..storage import (
    load_settings,
    save_settings,
    get_saved_password,
    set_saved_password,
    delete_saved_password,
)
from ..style import apply_stridebuddy_style


class LinkLabel(QLabel):
    """Clickable link-styled label."""

    clicked = Signal()

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "link")
        self.setObjectName("link")
        self.setStyleSheet("QLabel { color: #1e73be; }")

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class Banner(QWidget):
    """Top blue banner with the StrideBuddy runner icon."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setAutoFillBackground(True)
        self._bg = QColor("#1e73be")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        logo = QLabel(self)
        pix = QPixmap(asset_path("sb_runner.svg"))
        # Fallback: draw a simple circle if SVG failed to load
        if pix.isNull():
            pix = QPixmap(QSize(72, 72))
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor("#ffd54f"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRect(0, 0, 72, 72))
            p.end()
        logo.setPixmap(pix.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        title = QLabel("StrideBuddy")
        title.setStyleSheet(
            "QLabel { color: white; font-family: Tahoma; font-size: 20px; font-weight: bold; }"
        )

        layout.addWidget(logo, 0, Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(title, 1, Qt.AlignLeft | Qt.AlignVCenter)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.fillRect(self.rect(), self._bg)
        p.end()


class SignOnWindow(QMainWindow):
    """Main sign-on window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__} - Sign On")
        self.setWindowIcon(QIcon(asset_path("sb_runner.svg")))
        self.setFixedSize(320, 420)

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        root.addWidget(Banner(self))

        # Content area framed like classic AIM
        content_frame = QFrame(self)
        content_frame.setFrameShape(QFrame.StyledPanel)
        content_frame.setFrameShadow(QFrame.Sunken)
        content_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        root.addWidget(content_frame)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        content_layout.addLayout(grid)

        # Screen name row (labels placed above fields for visibility)
        screen_name_label = QLabel("ScreenName:")
        screen_name_label.setStyleSheet(
            "QLabel { color: #000000; padding-left: 6px; font-weight: 700; }"
        )
        self.screen_name = QComboBox()
        self.screen_name.setEditable(True)
        self.screen_name.setInsertPolicy(QComboBox.NoInsert)
        self.screen_name.setMaxVisibleItems(8)
        self.screen_name.setToolTip("Enter your screen name")
        self.screen_name.setFixedHeight(24)
        grid.addWidget(screen_name_label, 0, 0, 1, 2)
        grid.addItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed), 1, 0, 1, 2)
        grid.addWidget(self.screen_name, 2, 0, 1, 2)

        get_name = LinkLabel("Get a Screen Name")
        grid.addWidget(get_name, 3, 0, 1, 2, alignment=Qt.AlignLeft)
        # Extra breathing room before the Password section
        grid.addItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed), 4, 0, 1, 2)

        # Password row
        password_label = QLabel("Password")
        password_label.setStyleSheet(
            "QLabel { color: #000000; padding-left: 6px; font-weight: 700; }"
        )
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(24)
        grid.addWidget(password_label, 5, 0, 1, 2)
        grid.addItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed), 6, 0, 1, 2)
        grid.addWidget(self.password, 7, 0, 1, 2)

        self.saved_hint = LinkLabel("Saved - click here to change")
        self.saved_hint.setObjectName("savedHint")
        self.saved_hint.setStyleSheet("QLabel#savedHint { color: #666666; }")
        self.saved_hint.setVisible(False)
        grid.addWidget(self.saved_hint, 8, 0, 1, 2, alignment=Qt.AlignLeft)

        forgot = LinkLabel("Forgot Password?")
        grid.addWidget(forgot, 9, 0, 1, 2, alignment=Qt.AlignLeft)

        # Error feedback label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setStyleSheet("QLabel#errorLabel { color: #b91c1c; }")
        self.error_label.setVisible(False)
        grid.addWidget(self.error_label, 10, 0, 1, 2, alignment=Qt.AlignLeft)

        # Options
        options_row = QHBoxLayout()
        self.save_password = QCheckBox("Save password")
        self.save_password.setStyleSheet("QCheckBox { color: #000000; }")
        self.auto_login = QCheckBox("Auto-login")
        self.auto_login.setStyleSheet("QCheckBox { color: #000000; }")
        options_row.setSpacing(12)
        options_row.addWidget(self.save_password)
        options_row.addStretch(1)
        options_row.addWidget(self.auto_login)
        content_layout.addLayout(options_row)

        # Keep only a small gap before the buttons; avoid large empty space
        content_layout.addSpacing(6)

        # Buttons
        button_row = QHBoxLayout()
        self.help_btn = QPushButton("&Help")
        self.setup_btn = QPushButton("&Setup")
        self.signon_btn = QPushButton("&Sign On")
        self.signon_btn.setDefault(True)
        # Add green border to Help (to match Sign On outline)
        self.help_btn.setStyleSheet(
            "QPushButton { border: 1px solid #6ee7b7; border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:hover { border-color: #10b981; }"
        )
        # Add green border to Setup as well
        self.setup_btn.setStyleSheet(
            "QPushButton { border: 1px solid #6ee7b7; border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:hover { border-color: #10b981; }"
        )
        button_row.addWidget(self.help_btn)
        button_row.addWidget(self.setup_btn)
        button_row.addStretch(1)
        button_row.addWidget(self.signon_btn)
        root.addLayout(button_row)

        # Version label
        root.addStretch(1)  # Push version to the very bottom
        version = QLabel(f"Version: {__version__}")
        version.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        version.setStyleSheet("QLabel { color: #666666; }")
        root.addWidget(version)

        # Wire up behaviors
        self.signon_btn.clicked.connect(self._sign_on)
        get_name.clicked.connect(self._get_screen_name)
        forgot.clicked.connect(self._forgot_password)
        self.saved_hint.clicked.connect(self._clear_saved_password)
        self.help_btn.clicked.connect(self._open_help)
        self.setup_btn.clicked.connect(self._open_setup)
        # Clear errors when user edits fields
        self.password.textChanged.connect(lambda: self._clear_error())
        self.screen_name.editTextChanged.connect(self._on_screen_name_changed)

        # Load settings and maybe auto-login
        self._load_settings_and_maybe_autologin()

    # --- Behaviors (stubbed for now) ---
    def _sign_on(self) -> None:
        # Real login via local server
        screen_name = self.screen_name.currentText().strip()
        password = self.password.text()
        if not screen_name or not password:
            self._show_error("Enter screen name and password.")
            return
        self._clear_error()
        self.signon_btn.setEnabled(False)
        self.statusBar().showMessage("Signing on...", 1500)
        try:
            base_url = load_settings().get("server_url", "http://127.0.0.1:5000")
            # Use a persistent session so cookies (login) persist across API calls
            sess = requests.Session()
            resp = sess.post(
                f"{base_url}/api/auth/login",
                json={"screen_name": screen_name, "password": password},
                timeout=5,
            )
            data = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {}
            if resp.ok and data.get("ok"):
                self.statusBar().showMessage("Signed on.", 1000)
                # Persist preferences without clobbering other settings
                st = load_settings()
                st.update({
                    "last_screen_name": screen_name,
                    "save_password": self.save_password.isChecked(),
                    "auto_login": self.auto_login.isChecked(),
                })
                save_settings(st)
                if self.save_password.isChecked():
                    set_saved_password(screen_name, password)
                    self.saved_hint.setVisible(True)
                else:
                    delete_saved_password(screen_name)
                    self.saved_hint.setVisible(False)
                # Store session globally on the app so workers and windows can reuse it
                QApplication.instance().setProperty("sb_session", sess)
                self._open_buddy_list()
            else:
                self._show_error(data.get("error") or "Invalid screen name or password.")
        except Exception as e:
            self._show_error("Auth server not reachable. Start the server.")
        finally:
            self.signon_btn.setEnabled(True)

    def _get_screen_name(self) -> None:
        base_url = load_settings().get("server_url", "http://127.0.0.1:5000")
        webbrowser.open(f"{base_url}/signup")

    def _forgot_password(self) -> None:
        base_url = load_settings().get("server_url", "http://127.0.0.1:5000")
        webbrowser.open(f"{base_url}/forgot")

    def _open_help(self) -> None:
        base_url = load_settings().get("server_url", "http://127.0.0.1:5000")
        webbrowser.open(f"{base_url}/help")

    def _open_buddy_list(self) -> None:
        # Determine local screen name to pass to child windows
        local_name = self.screen_name.currentText().strip() or "You"
        self._buddy = BuddyListWindow(local_name, on_signoff=self._on_signed_off)
        self._buddy.show()
        self.hide()

    def _on_signed_off(self) -> None:
        # Show the sign-on window again and focus password for quick re-login
        self.show()
        self.raise_()
        self.activateWindow()
        self.password.setFocus()
        self.statusBar().showMessage("Signed off.", 2000)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        # Highlight fields
        self.password.setStyleSheet("QLineEdit { border: 1px solid #e11d48; }")
        self.screen_name.setStyleSheet("QComboBox { border: 1px solid #e11d48; }")
        self.statusBar().showMessage(message, 4000)

    def _clear_error(self) -> None:
        if self.error_label.isVisible():
            self.error_label.setVisible(False)
        # Reset field styles
        self.password.setStyleSheet("")
        self.screen_name.setStyleSheet("")

    # --- Settings & saved password helpers ---
    def _load_settings_and_maybe_autologin(self) -> None:
        st = load_settings()
        last = st.get("last_screen_name") or ""
        save_pw = bool(st.get("save_password"))
        auto = bool(st.get("auto_login"))
        if last:
            self.screen_name.setEditText(last)
        self.save_password.setChecked(save_pw)
        self.auto_login.setChecked(auto)

        pwd = get_saved_password(last) if save_pw and last else None
        if pwd:
            self.password.setText(pwd)
            self.saved_hint.setVisible(True)
        else:
            self.saved_hint.setVisible(False)

        if auto and last and pwd:
            QTimer.singleShot(300, self._sign_on)

    def _on_screen_name_changed(self, *_args) -> None:
        self._clear_error()
        name = self.screen_name.currentText().strip()
        pwd = get_saved_password(name)
        if pwd:
            self.password.setText(pwd)
            self.saved_hint.setVisible(True)
        else:
            self.password.clear()
            self.saved_hint.setVisible(False)

    def _clear_saved_password(self) -> None:
        name = self.screen_name.currentText().strip()
        delete_saved_password(name)
        self.password.clear()
        self.saved_hint.setVisible(False)
        self.statusBar().showMessage("Saved password cleared.", 2000)

    # --- Setup dialog ---
    def _open_setup(self) -> None:
        dlg = SetupDialog(self)
        if dlg.exec() == QDialog.Accepted:
            st = load_settings()
            # Re-apply style globally based on new settings
            apply_stridebuddy_style(QApplication.instance(), st)
            self.screen_name.setEditText(st.get("last_screen_name", ""))
            self.save_password.setChecked(bool(st.get("save_password")))
            self.auto_login.setChecked(bool(st.get("auto_login")))
            pwd = get_saved_password(self.screen_name.currentText().strip())
            self.saved_hint.setVisible(bool(pwd))


