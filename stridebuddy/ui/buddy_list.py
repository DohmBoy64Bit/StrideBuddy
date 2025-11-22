from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QFrame,
)

from .. import __app_name__
from ..resources import asset_path
from .message_window import MessageWindow


class BuddyListWindow(QMainWindow):
    """A minimal nostalgic buddy list window with grouped buddies."""

    def __init__(self, local_screen_name: str, on_signoff=None) -> None:
        super().__init__()
        self.local_screen_name = local_screen_name
        self._on_signoff = on_signoff
        self.setWindowTitle(f"{__app_name__} - Buddy List")
        self.setWindowIcon(QIcon(asset_path("sb_runner.svg")))
        self.setFixedSize(260, 460)

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Header with small status/search
        header = QHBoxLayout()
        header.setSpacing(6)
        self.status_edit = QLineEdit()
        self.status_edit.setPlaceholderText("Type a status message…")
        header.addWidget(self.status_edit)
        root.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        root.addWidget(line)

        # Buddy Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        root.addWidget(self.tree, 1)

        # Sample data (placeholder)
        self._populate_sample()

        # Footer buttons
        footer = QHBoxLayout()
        self.add_btn = QPushButton("&Add Buddy")
        self.signoff_btn = QPushButton("Sign &Off")
        # Match Sign On's green-accented border style
        self.signoff_btn.setStyleSheet(
            "QPushButton { border: 1px solid #6ee7b7; border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:hover { border-color: #10b981; }"
        )
        footer.addWidget(self.add_btn)
        footer.addStretch(1)
        footer.addWidget(self.signoff_btn)
        root.addLayout(footer)

        self.signoff_btn.clicked.connect(self._handle_signoff)

    def _populate_sample(self) -> None:
        groups = {
            "Buddies": [("alex", True), ("jordan", False)],
            "Work": [("patricia", True)],
            "Family": [("mom", False), ("dad", True)],
        }
        for group_name, buddies in groups.items():
            group_item = QTreeWidgetItem([group_name])
            group_item.setFirstColumnSpanned(True)
            group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(group_item)
            for name, online in buddies:
                label = f"{name} {'(online)' if online else '(away)'}"
                child = QTreeWidgetItem([label])
                group_item.addChild(child)
            group_item.setExpanded(True)

        # Open a message window on buddy double-click
        self.tree.itemDoubleClicked.connect(self._open_message_for_item)

    def _open_message_for_item(self, item: QTreeWidgetItem, column: int) -> None:
        if item.childCount() > 0:
            return
        label = item.text(0)
        screen_name = label.split(" ", 1)[0]
        msg = MessageWindow(screen_name, self.local_screen_name)
        msg.show()
        # Store reference to prevent GC
        if not hasattr(self, "_open_msgs"):
            self._open_msgs = []
        self._open_msgs.append(msg)

    def _handle_signoff(self) -> None:
        # Close any open message windows
        if hasattr(self, "_open_msgs"):
            for w in list(self._open_msgs):
                try:
                    w.close()
                except Exception:
                    pass
            self._open_msgs.clear()
        # Notify parent and close
        if callable(self._on_signoff):
            try:
                self._on_signoff()
            except Exception:
                pass
        self.close()


