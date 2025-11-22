from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QInputDialog,
    QMenu,
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
from ..storage import load_settings
import requests
from PySide6.QtWidgets import QApplication
import time


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
        self.add_btn.clicked.connect(self._add_buddy_dialog)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._open_context_menu)

        # Networking worker thread (smooth UI)
        self._base_url = load_settings().get("server_url", "http://127.0.0.1:5000")
        self._net_thread = QThread(self)
        self._net_worker = _NetWorker(self._base_url, self.local_screen_name)
        self._net_worker.moveToThread(self._net_thread)
        self._net_thread.started.connect(self._net_worker.run)
        self._net_worker.messages.connect(self._on_messages)
        self._net_worker.online.connect(self._on_online)
        self._net_thread.start()
        # Initial fetch of buddies from server
        self._refresh_buddies()

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
        # Reuse existing window if already open
        if not hasattr(self, "_open_msgs"):
            self._open_msgs = []
        for w in self._open_msgs:
            if getattr(w, "peer_screen_name", "") == screen_name:
                w.show()
                w.raise_()
                w.activateWindow()
                return
        msg = MessageWindow(screen_name, self.local_screen_name)
        msg.show()
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

    # --- Networking ---
    def _on_messages(self, msgs: list[dict]) -> None:
        for m in msgs or []:
            sender = m.get("from") or "buddy"
            text = m.get("content") or ""
            self._deliver_incoming(sender, text)

    def _deliver_incoming(self, sender: str, text: str) -> None:
        # Notify via tray
        tray = QApplication.instance().property("sb_tray")
        if tray:
            tray.showMessage(sender, text[:80], QIcon(asset_path("sb_runner.svg")), 2500)
        # Open or find message window
        if not hasattr(self, "_open_msgs"):
            self._open_msgs = []
        target = None
        for w in self._open_msgs:
            if getattr(w, "peer_screen_name", "") == sender:
                target = w
                break
        if target is None:
            msg = MessageWindow(sender, self.local_screen_name)
            msg.show()
            self._open_msgs.append(msg)
            target = msg
        # Append incoming
        if hasattr(target, "append_incoming"):
            target.append_incoming(text)

    def _on_online(self, names: list[str]) -> None:
        # Update simple suffix on known buddies
        try:
            for i in range(self.tree.topLevelItemCount()):
                group = self.tree.topLevelItem(i)
                for j in range(group.childCount()):
                    child = group.child(j)
                    base = (child.text(0).split(" ", 1)[0]).strip()
                    status = "(online)" if base in names else "(away)"
                    child.setText(0, f"{base} {status}")
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        # Ensure worker stops
        try:
            self._net_worker.stop()
            self._net_thread.quit()
            self._net_thread.wait(1500)
        except Exception:
            pass
        super().closeEvent(event)

    def _refresh_buddies(self) -> None:
        # Fetch buddies from server and render groups
        try:
            r = requests.get(f"{self._base_url}/api/buddies", params={"owner": self.local_screen_name}, timeout=5)
            data = r.json() if r.ok else {}
            buddies = data.get("buddies", [])
            self.tree.clear()
            group_map: dict[str, QTreeWidgetItem] = {}
            for entry in buddies:
                bname = entry.get("buddy") or ""
                grp = entry.get("group") or "Buddies"
                if grp not in group_map:
                    group_item = QTreeWidgetItem([grp])
                    group_item.setFirstColumnSpanned(True)
                    group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
                    self.tree.addTopLevelItem(group_item)
                    group_item.setExpanded(True)
                    group_map[grp] = group_item
                child = QTreeWidgetItem([f"{bname} (away)"])
                group_map[grp].addChild(child)
            if not buddies:
                # keep sample if empty
                self._populate_sample()
        except Exception:
            # fallback to sample on error
            self._populate_sample()

    def _add_buddy_dialog(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Buddy", "Screen name:")
        if not ok or not name.strip():
            return
        group, ok = QInputDialog.getText(self, "Add Buddy", "Group (optional):")
        if not ok:
            return
        try:
            payload = {"owner": self.local_screen_name, "buddy": name.strip(), "group": (group.strip() or None)}
            r = requests.post(f"{self._base_url}/api/buddies", json=payload, timeout=5)
            if r.ok:
                self._refresh_buddies()
        except Exception:
            pass

    def _open_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item or item.childCount() > 0:
            return
        menu = QMenu(self)
        # Ensure visibility on dark backgrounds
        menu.setStyleSheet(
            "QMenu { color: white; }"
            "QMenu::item:selected { background: #1e73be; }"
        )
        menu.addAction("Remove Buddy", lambda: self._remove_buddy(item))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _remove_buddy(self, item: QTreeWidgetItem) -> None:
        name = (item.text(0).split(" ", 1)[0]).strip()
        try:
            r = requests.delete(f"{self._base_url}/api/buddies", json={"owner": self.local_screen_name, "buddy": name}, timeout=5)
            if r.ok:
                self._refresh_buddies()
        except Exception:
            pass


class _NetWorker(QObject):
    messages = Signal(list)
    online = Signal(list)

    def __init__(self, base_url: str, screen_name: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.screen_name = screen_name
        self._running = True
        self._session = requests.Session()

    def stop(self) -> None:
        self._running = False
        try:
            self._session.close()
        except Exception:
            pass

    def run(self) -> None:
        last_online_check = 0.0
        while self._running:
            now = time.time()
            # Heartbeat
            try:
                self._session.post(f"{self.base_url}/api/presence/heartbeat", json={"screen_name": self.screen_name}, timeout=3)
            except Exception:
                pass
            # Online list every 7s
            if now - last_online_check > 7:
                try:
                    r = self._session.get(f"{self.base_url}/api/presence/online", timeout=3)
                    data = r.json() if r.ok else {}
                    self.online.emit(data.get("online", []))
                except Exception:
                    pass
                last_online_check = now
            # Short long-poll messages (keep small so we can stop fast)
            try:
                r = self._session.get(
                    f"{self.base_url}/api/messages/poll",
                    params={"screen_name": self.screen_name, "timeout": 3},
                    timeout=4,
                )
                data = r.json() if r.ok else {}
                msgs = data.get("messages", [])
                if msgs:
                    self.messages.emit(msgs)
            except Exception:
                time.sleep(0.5)


