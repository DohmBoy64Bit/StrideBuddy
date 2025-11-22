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
    QMessageBox,
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

        # Enable basic drag & drop within a group (optional polish)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)

        # Footer buttons
        footer = QHBoxLayout()
        self.add_btn = QPushButton("&Add Buddy")
        self.signoff_btn = QPushButton("Sign &Off")
        # Match Sign On's green-accented border style
        self.add_btn.setStyleSheet(
            "QPushButton { border: 1px solid #6ee7b7; border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:hover { border-color: #10b981; }"
        )
        self.signoff_btn.setStyleSheet(
            "QPushButton { border: 1px solid #6ee7b7; border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:hover { border-color: #10b981; }"
        )
        footer.addWidget(self.add_btn)
        footer.addStretch(1)
        self.conn_label = QLabel("Connected")
        self.conn_label.setStyleSheet("QLabel { color: #666666; }")
        footer.addWidget(self.conn_label)
        footer.addWidget(self.signoff_btn)
        root.addLayout(footer)

        self.signoff_btn.clicked.connect(self._handle_signoff)
        self.add_btn.clicked.connect(self._add_buddy_dialog)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._open_context_menu)

        # Networking worker thread (smooth UI)
        self._base_url = load_settings().get("server_url", "http://127.0.0.1:5000")
        self._session = QApplication.instance().property("sb_session")
        self._net_thread = QThread(self)
        # Track last user activity (typing status message or focusing window)
        self._last_input = time.time()
        self.status_edit.textChanged.connect(lambda: setattr(self, "_last_input", time.time()))
        self._net_worker = _NetWorker(
            self._base_url,
            self.local_screen_name,
            self._session,
            get_active=lambda: (time.time() - getattr(self, "_last_input", 0)) < 60,
            get_names=lambda: list((self._buddy_flags or {}).keys()),
        )
        self._net_worker.moveToThread(self._net_thread)
        self._net_thread.started.connect(self._net_worker.run)
        self._net_worker.messages.connect(self._on_messages)
        self._net_worker.online.connect(self._on_online)
        self._net_worker.typing.connect(self._on_typing)
        self._net_worker.state.connect(self._on_state)
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
            html = m.get("content_html") or ""
            self._deliver_incoming(sender, text, html)

    def _deliver_incoming(self, sender: str, text: str, html: str = "") -> None:
        # Notify via tray
        tray = QApplication.instance().property("sb_tray")
        if tray:
            # Respect mute flag
            flags = (self._buddy_flags or {}).get(sender, {})
            if not bool(flags.get("muted")):
                tray.showMessage(sender, text[:80], QIcon(asset_path("sb_runner.svg")), 2500)
        # Drop entirely if blocked
        flags = (self._buddy_flags or {}).get(sender, {})
        if bool(flags.get("blocked")):
            return
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
            target.append_incoming(text, html)

    def _on_online(self, statuses: object) -> None:
        # Update status (online/away/offline) and preserve flags
        try:
            names = statuses or {}
            for i in range(self.tree.topLevelItemCount()):
                group = self.tree.topLevelItem(i)
                for j in range(group.childCount()):
                    child = group.child(j)
                    base = (child.text(0).split(" ", 1)[0]).strip()
                    state = str(names.get(base, "offline"))
                    status = {"online": "(online)", "away": "(away)", "offline": "(offline)"}.get(state, "(offline)")
                    # Preserve flags in the label
                    flags = (self._buddy_flags or {}).get(base, {})
                    tag = ""
                    if bool(flags.get("blocked")):
                        tag = " [blocked]"
                    elif bool(flags.get("muted")):
                        tag = " [muted]"
                    child.setText(0, f"{base} {status}{tag}")
        except Exception:
            pass

    def _on_typing(self, typers: list[str]) -> None:
        # Show typing indicator on corresponding message windows
        if not hasattr(self, "_open_msgs"):
            return
        for name in typers or []:
            for w in self._open_msgs:
                if getattr(w, "peer_screen_name", "") == name and hasattr(w, "statusBar"):
                    w.statusBar().showMessage(f"{name} is typing…", 1500)

    def _on_state(self, st: str) -> None:
        if not hasattr(self, "conn_label"):
            return
        if st == "connected":
            self.conn_label.setText("Connected")
            self.conn_label.setStyleSheet("QLabel { color: #16a34a; }")
        elif st == "reconnecting":
            self.conn_label.setText("Reconnecting…")
            self.conn_label.setStyleSheet("QLabel { color: #ca8a04; }")
        elif st == "unauthorized":
            self.conn_label.setText("Unauthorized")
            self.conn_label.setStyleSheet("QLabel { color: #dc2626; }")
        else:
            self.conn_label.setText(st)
            self.conn_label.setStyleSheet("QLabel { color: #666666; }")

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
            sess = self._session or requests.Session()
            r = sess.get(f"{self._base_url}/api/buddies", timeout=5)
            data = r.json() if r.ok else {}
            buddies = data.get("buddies", [])
            self.tree.clear()
            group_map: dict[str, QTreeWidgetItem] = {}
            self._buddy_flags = {}
            for entry in buddies:
                bname = entry.get("buddy") or ""
                grp = entry.get("group") or "Buddies"
                muted = bool(int(entry.get("muted", 0)))
                blocked = bool(int(entry.get("blocked", 0)))
                self._buddy_flags[bname] = {"muted": muted, "blocked": blocked}
                if grp not in group_map:
                    group_item = QTreeWidgetItem([grp])
                    group_item.setFirstColumnSpanned(True)
                    group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
                    self.tree.addTopLevelItem(group_item)
                    group_item.setExpanded(True)
                    group_map[grp] = group_item
                suffix = " (away)"
                if blocked:
                    suffix += " [blocked]"
                elif muted:
                    suffix += " [muted]"
                child = QTreeWidgetItem([f"{bname}{suffix}"])
                group_map[grp].addChild(child)
            if not buddies:
                # keep sample if empty
                self._populate_sample()
        except Exception:
            # fallback to sample on error
            self._populate_sample()

    def _add_buddy_dialog(self) -> None:
        # Screen name prompt with black label
        name_dlg = QInputDialog(self)
        name_dlg.setWindowTitle("Add Buddy")
        name_dlg.setLabelText("Screen name:")
        name_dlg.setInputMode(QInputDialog.TextInput)
        name_dlg.setStyleSheet("QInputDialog QLabel { color: black; }")
        ok = name_dlg.exec()
        name = name_dlg.textValue()
        if not ok or not name.strip():
            return
        # Group prompt with black label
        group_dlg = QInputDialog(self)
        group_dlg.setWindowTitle("Add Buddy")
        group_dlg.setLabelText("Group (optional):")
        group_dlg.setInputMode(QInputDialog.TextInput)
        group_dlg.setStyleSheet("QInputDialog QLabel { color: black; }")
        ok = group_dlg.exec()
        group = group_dlg.textValue()
        if not ok:
            return
        try:
            payload = {"buddy": name.strip(), "group": (group.strip() or None)}
            sess = self._session or requests.Session()
            r = sess.post(f"{self._base_url}/api/buddies", json=payload, timeout=5)
            if r.ok and (r.headers.get("content-type","").startswith("application/json")) and (r.json().get("ok")):
                self._refresh_buddies()
            else:
                # Try to extract server error for user-friendly message
                err = ""
                try:
                    data = r.json()
                    err = data.get("error") or ""
                except Exception:
                    pass
                if r.status_code == 404 and not err:
                    err = "User not found."
                if r.status_code == 401 and not err:
                    err = "Please sign in again."
                if not err:
                    err = f"Could not add buddy (HTTP {r.status_code})."
                mb = QMessageBox(self)
                mb.setWindowTitle("Add Buddy")
                mb.setText(err)
                mb.setIcon(QMessageBox.Warning)
                mb.setStyleSheet("QMessageBox QLabel { color: black; }")
                mb.exec()
        except Exception:
            mb = QMessageBox(self)
            mb.setWindowTitle("Add Buddy")
            mb.setText("Network error. Please try again.")
            mb.setIcon(QMessageBox.Warning)
            mb.setStyleSheet("QMessageBox QLabel { color: black; }")
            mb.exec()

    def _open_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { color: white; } QMenu::item:selected { background: #1e73be; }")
        if item.childCount() > 0:  # group
            grp_name = item.text(0)
            menu.addAction("Rename Group...", lambda: self._rename_group(grp_name))
        else:  # buddy
            name = (item.text(0).split(" ", 1)[0]).strip()
            menu.addAction("Remove Buddy", lambda: self._remove_buddy(item))
            flags = (self._buddy_flags or {}).get(name, {})
            muted = bool(flags.get("muted"))
            blocked = bool(flags.get("blocked"))
            if blocked:
                menu.addAction("Unblock", lambda: self._set_flags(name, blocked=False))
            else:
                menu.addAction("Block", lambda: self._set_flags(name, blocked=True))
            if muted:
                menu.addAction("Unmute", lambda: self._set_flags(name, muted=False))
            else:
                menu.addAction("Mute", lambda: self._set_flags(name, muted=True))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _remove_buddy(self, item: QTreeWidgetItem) -> None:
        name = (item.text(0).split(" ", 1)[0]).strip()
        try:
            sess = self._session or requests.Session()
            r = sess.delete(f"{self._base_url}/api/buddies", json={"buddy": name}, timeout=5)
            if r.ok:
                self._refresh_buddies()
        except Exception:
            pass

    def _rename_group(self, old: str) -> None:
        new, ok = QInputDialog.getText(self, "Rename Group", f"New name for '{old}':")
        if not ok or not new.strip() or new.strip() == old:
            return
        try:
            sess = self._session or requests.Session()
            r = sess.post(f"{self._base_url}/api/buddies/rename_group", json={"old_group": old, "new_group": new.strip()}, timeout=5)
            if r.ok:
                self._refresh_buddies()
        except Exception:
            pass

    def _set_flags(self, name: str, muted: bool | None = None, blocked: bool | None = None) -> None:
        payload = {"buddy": name}
        if muted is not None:
            payload["muted"] = muted
        if blocked is not None:
            payload["blocked"] = blocked
        try:
            sess = self._session or requests.Session()
            r = sess.post(f"{self._base_url}/api/buddies/set_flags", json=payload, timeout=5)
            if r.ok:
                self._refresh_buddies()
        except Exception:
            pass

class _NetWorker(QObject):
    messages = Signal(list)
    online = Signal(object)  # dict name->status
    typing = Signal(list)
    state = Signal(str)  # "connected"|"reconnecting"|"unauthorized"

    def __init__(self, base_url: str, screen_name: str, session=None, get_active=None, get_names=None) -> None:
        super().__init__()
        self.base_url = base_url
        self.screen_name = screen_name
        self._running = True
        self._session = session or requests.Session()
        self._get_active = get_active  # callable -> bool
        self._get_names = get_names    # callable -> list[str]

    def stop(self) -> None:
        self._running = False
        try:
            self._session.close()
        except Exception:
            pass

    def run(self) -> None:
        last_online_check = 0.0
        last_typing_check = 0.0
        backoff = 1.0
        while self._running:
            now = time.time()
            # Heartbeat
            try:
                active = False
                try:
                    if self._get_active:
                        active = bool(self._get_active())
                except Exception:
                    active = False
                self._session.post(f"{self.base_url}/api/presence/heartbeat", json={"active": active}, timeout=3)
                self.state.emit("connected")
                backoff = 1.0
            except Exception:
                self.state.emit("reconnecting")
                time.sleep(min(backoff, 8.0))
                backoff = min(backoff * 2.0, 8.0)
                continue
            # Online list every 7s
            if now - last_online_check > 7:
                try:
                    names = []
                    try:
                        if self._get_names:
                            names = list(self._get_names() or [])
                    except Exception:
                        names = []
                    if names:
                        r = self._session.get(f"{self.base_url}/api/presence/status", params={"names": ",".join(names)}, timeout=4)
                        if r.status_code == 401:
                            self.state.emit("unauthorized")
                            time.sleep(2.0)
                            continue
                        data = r.json() if r.ok else {}
                        self.online.emit(data.get("statuses", {}))
                except Exception:
                    pass
                last_online_check = now
            # Poll typing frequently (~1s)
            if now - last_typing_check > 1.0:
                try:
                    rt = self._session.get(f"{self.base_url}/api/messages/typing", timeout=3)
                    td = rt.json() if rt.ok else {}
                    if td.get("typing"):
                        self.typing.emit(td.get("typing"))
                except Exception:
                    pass
                last_typing_check = now
            # Short long-poll messages (keep small so we can stop fast)
            try:
                r = self._session.get(
                    f"{self.base_url}/api/messages/poll",
                    params={"screen_name": self.screen_name, "timeout": 3},
                    timeout=4,
                )
                if r.status_code == 401:
                    self.state.emit("unauthorized")
                    time.sleep(2.0)
                    continue
                data = r.json() if r.ok else {}
                msgs = data.get("messages", [])
                if msgs:
                    self.messages.emit(msgs)
            except Exception:
                time.sleep(0.5)


