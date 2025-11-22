from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import (
    QIcon,
    QTextCursor,
    QAction,
    QTextCharFormat,
    QFont,
    QColor,
    QTextBlockFormat,
    QTextDocumentFragment,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QToolBar,
    QMenuBar,
    QSizePolicy,
    QColorDialog,
    QInputDialog,
    QMenu,
    QTextBrowser,
)

from .. import __app_name__
from ..resources import asset_path


class MessageWindow(QMainWindow):
    """StrideBuddy message window with transcript, input box, and classic actions."""

    def __init__(self, peer_screen_name: str, local_screen_name: str) -> None:
        super().__init__()
        self.peer_screen_name = peer_screen_name
        self.local_screen_name = local_screen_name
        self.setWindowTitle(f"{__app_name__} – Message with {peer_screen_name}")
        self.setWindowIcon(QIcon(asset_path("sb_runner.svg")))
        self.setMinimumSize(520, 520)
        self.resize(540, 560)

        # Menu bar (placeholder items for nostalgia)
        self._build_menubar()

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(6)

        # Transcript (read-only, supports clicking links)
        self.transcript = QTextBrowser()
        self.transcript.setReadOnly(True)
        self.transcript.setOpenExternalLinks(True)
        self.transcript.setPlaceholderText(f"Chat with {peer_screen_name} will appear here…")
        root.addWidget(self.transcript, 2)

        # Prepare input editor first so toolbar can connect signals
        self.input = QTextEdit()
        self.input.setPlaceholderText("Type a message…")
        self.input.setFixedHeight(110)

        # Formatting toolbar (lightweight, text-based)
        self.fmt_toolbar = QToolBar()
        self.fmt_toolbar.setIconSize(self.fmt_toolbar.iconSize())  # default
        self._add_format_actions(self.fmt_toolbar)
        root.addWidget(self.fmt_toolbar)

        # Input area (rendered below toolbar)
        root.addWidget(self.input, 1)

        # Bottom actions (keep Warn/Block, add Expressions and Send; no Talk/Games)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self.warn_btn = QPushButton("Warn")
        self.block_btn = QPushButton("Block")
        self.emote_btn = QPushButton("Expressions")
        actions_row.addWidget(self.warn_btn)
        actions_row.addWidget(self.block_btn)
        actions_row.addWidget(self.emote_btn)
        actions_row.addStretch(1)
        self.send_btn = QPushButton("Send")
        self.send_btn.setDefault(True)
        actions_row.addWidget(self.send_btn)
        root.addLayout(actions_row)

        # Wire actions
        self.send_btn.clicked.connect(self._send_message)
        self.input.installEventFilter(self)
        self.warn_btn.clicked.connect(self._warn_peer)
        self.block_btn.clicked.connect(self._block_peer)

        # Status line
        self.statusBar().showMessage(f"Chatting with {peer_screen_name}")

    def _build_menubar(self) -> None:
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        for name in ["File", "Edit", "Insert", "People"]:
            menu = menubar.addMenu(name)
            # Populate with minimal placeholders
            if name == "File":
                menu.addAction("Close", self.close)
            else:
                menu.addAction("No actions yet")

    def _add_format_actions(self, tb: QToolBar) -> None:
        self.act_bold = QAction("B", self)
        self.act_bold.setCheckable(True)
        self.act_bold.triggered.connect(self._toggle_bold)
        self.act_italic = QAction("I", self)
        self.act_italic.setCheckable(True)
        self.act_italic.triggered.connect(self._toggle_italic)
        self.act_underline = QAction("U", self)
        self.act_underline.setCheckable(True)
        self.act_underline.triggered.connect(self._toggle_underline)
        tb.addAction(self.act_bold)
        tb.addAction(self.act_italic)
        tb.addAction(self.act_underline)
        tb.addSeparator()
        self.act_color = QAction("A", self)
        self.act_color.triggered.connect(self._choose_color)
        tb.addAction(self.act_color)
        self.act_link = QAction("link", self)
        self.act_link.triggered.connect(self._insert_link)
        tb.addAction(self.act_link)
        self.act_emoji = QAction("☺", self)
        self.act_emoji.triggered.connect(self._show_emoji_menu)
        tb.addAction(self.act_emoji)

        # Keep toolbar toggles in sync with cursor
        self.input.cursorPositionChanged.connect(self._sync_toolbar_from_cursor)

    def _append_to_transcript(self, sender: str, text: str | None = None, fragment: QTextDocumentFragment | None = None) -> None:
        """Append a message like: You (9:12 PM): message, with wrapping."""
        timestamp = datetime.now().strftime("%I:%M %p").lstrip("0")

        cursor = self.transcript.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Begin a new paragraph for this message with tight spacing
        block_fmt = QTextBlockFormat()
        block_fmt.setTopMargin(2)
        block_fmt.setBottomMargin(2)
        cursor.insertBlock(block_fmt)

        # Sender (bold)
        sender_fmt = QTextCharFormat()
        sender_fmt.setFontWeight(QFont.Weight.Bold)
        cursor.insertText(sender, sender_fmt)

        # Space + timestamp (grey)
        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(QColor("#666666"))
        cursor.insertText(f" ({timestamp})", ts_fmt)

        # Colon + space and the actual message (rich or plain, wraps automatically)
        cursor.insertText(": ")
        if fragment is not None:
            cursor.insertFragment(fragment)
        elif text is not None:
            cursor.insertText(text)

        self.transcript.setTextCursor(cursor)

    def _send_message(self) -> None:
        plain = self.input.toPlainText().strip()
        if not plain:
            return
        frag = QTextDocumentFragment(self.input.document())
        self._append_to_transcript(self.local_screen_name, fragment=frag)
        self.input.clear()
        # TODO: hook to actual send over network

    def _warn_peer(self) -> None:
        self.statusBar().showMessage("Warned user (placeholder).", 2000)

    def _block_peer(self) -> None:
        self.statusBar().showMessage("Blocked user (placeholder).", 2000)

    def eventFilter(self, obj, event):  # type: ignore[override]
        # Ctrl+Enter or Enter to send (like classic IM apps)
        if obj is self.input and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter) and (
                event.modifiers() & Qt.ControlModifier or event.modifiers() == Qt.NoModifier
            ):
                self._send_message()
                return True
        return super().eventFilter(obj, event)

    # --- Formatting helpers ---
    def _apply_char_format(self, fmt: QTextCharFormat) -> None:
        cursor = self.input.textCursor()
        if not cursor.hasSelection():
            # Affect the typing attributes
            self.input.mergeCurrentCharFormat(fmt)
        else:
            cursor.mergeCharFormat(fmt)
            self.input.setTextCursor(cursor)

    def _toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.act_bold.isChecked() else QFont.Weight.Normal)
        self._apply_char_format(fmt)

    def _toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.act_italic.isChecked())
        self._apply_char_format(fmt)

    def _toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.act_underline.isChecked())
        self._apply_char_format(fmt)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(parent=self, title="Choose text color")
        if not color.isValid():
            return
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        self._apply_char_format(fmt)

    def _insert_link(self) -> None:
        url, ok = QInputDialog.getText(self, "Insert Link", "URL (https://...):")
        if not ok or not url.strip():
            return
        url = url.strip()
        cursor = self.input.textCursor()
        link_text = cursor.selectedText() or url
        fmt = QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(url)
        fmt.setForeground(QColor("#1e73be"))
        fmt.setFontUnderline(True)
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            cursor.insertText(link_text, fmt)
        self.input.setTextCursor(cursor)

    def _show_emoji_menu(self) -> None:
        if not hasattr(self, "_emoji_menu"):
            self._emoji_menu = QMenu(self)
            emojis = ["😀", "😃", "😄", "😉", "😊", "😍", "😂", "👍", "🎉", "❤️", "🔥", "🙂", "😎"]
            for e in emojis:
                self._emoji_menu.addAction(e, lambda ch=False, x=e: self._insert_emoji(x))
        pos = self.fmt_toolbar.mapToGlobal(self.fmt_toolbar.actionGeometry(self.act_emoji).bottomRight())
        self._emoji_menu.popup(pos)

    def _insert_emoji(self, emoji: str) -> None:
        cursor = self.input.textCursor()
        cursor.insertText(emoji)
        self.input.setTextCursor(cursor)

    def _sync_toolbar_from_cursor(self) -> None:
        fmt = self.input.currentCharFormat()
        self.act_bold.blockSignals(True)
        self.act_italic.blockSignals(True)
        self.act_underline.blockSignals(True)
        self.act_bold.setChecked(fmt.fontWeight() > QFont.Weight.Normal)
        self.act_italic.setChecked(fmt.fontItalic())
        self.act_underline.setChecked(fmt.fontUnderline())
        self.act_bold.blockSignals(False)
        self.act_italic.blockSignals(False)
        self.act_underline.blockSignals(False)


