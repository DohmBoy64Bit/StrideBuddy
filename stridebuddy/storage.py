from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import keyring

APP_NAME = "StrideBuddy"


def get_app_dir() -> Path:
    # Prefer roaming app data on Windows
    base = os.getenv("APPDATA")
    if base:
        path = Path(base) / APP_NAME
    else:
        path = Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return get_app_dir() / "settings.json"


def load_settings() -> Dict[str, Any]:
    p = settings_path()
    if not p.exists():
        return {
            "last_screen_name": "",
            "save_password": False,
            "auto_login": False,
            "server_url": "http://127.0.0.1:5000",
            "notifications_sounds": True,
            "notifications_toasts": True,
            "chat_default_bold": False,
            "chat_default_italic": False,
            "chat_allow_links": True,
            "chat_emoji_replace": True,
            "chat_transcripts_enabled": False,
            "appearance_theme": "Light",
            "appearance_compact": False,
            "appearance_timestamp_format": "12h",
            "appearance_font_size": 9,
            "privacy_buddies_only": False,
            "privacy_warn_confirm": True,
            "saved_accounts": [],
        }
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # ensure defaults
        data.setdefault("last_screen_name", "")
        data.setdefault("save_password", False)
        data.setdefault("auto_login", False)
        data.setdefault("server_url", "http://127.0.0.1:5000")
        data.setdefault("notifications_sounds", True)
        data.setdefault("notifications_toasts", True)
        data.setdefault("chat_default_bold", False)
        data.setdefault("chat_default_italic", False)
        data.setdefault("chat_allow_links", True)
        data.setdefault("chat_emoji_replace", True)
        data.setdefault("chat_transcripts_enabled", False)
        data.setdefault("appearance_theme", "Light")
        data.setdefault("appearance_compact", False)
        data.setdefault("appearance_timestamp_format", "12h")
        data.setdefault("appearance_font_size", 9)
        data.setdefault("privacy_buddies_only", False)
        data.setdefault("privacy_warn_confirm", True)
        data.setdefault("saved_accounts", [])
        return data
    except Exception:
        return {
            "last_screen_name": "",
            "save_password": False,
            "auto_login": False,
            "server_url": "http://127.0.0.1:5000",
            "notifications_sounds": True,
            "notifications_toasts": True,
            "chat_default_bold": False,
            "chat_default_italic": False,
            "chat_allow_links": True,
            "chat_emoji_replace": True,
            "chat_transcripts_enabled": False,
            "appearance_theme": "Light",
            "appearance_compact": False,
            "appearance_timestamp_format": "12h",
            "appearance_font_size": 9,
            "privacy_buddies_only": False,
            "privacy_warn_confirm": True,
            "saved_accounts": [],
        }


def save_settings(data: Dict[str, Any]) -> None:
    p = settings_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def get_saved_password(screen_name: str) -> str | None:
    if not screen_name:
        return None
    return keyring.get_password(APP_NAME, screen_name)


def set_saved_password(screen_name: str, password: str) -> None:
    if screen_name and password:
        keyring.set_password(APP_NAME, screen_name, password)
        # Track saved accounts for convenience
        st = load_settings()
        accs = set(st.get("saved_accounts", []))
        accs.add(screen_name)
        st["saved_accounts"] = sorted(accs)
        save_settings(st)


def delete_saved_password(screen_name: str) -> None:
    if not screen_name:
        return
    try:
        keyring.delete_password(APP_NAME, screen_name)
    except keyring.errors.PasswordDeleteError:
        pass
    # Remove from saved list
    st = load_settings()
    if "saved_accounts" in st and screen_name in st["saved_accounts"]:
        st["saved_accounts"] = [a for a in st["saved_accounts"] if a != screen_name]
        save_settings(st)


def list_saved_accounts() -> list[str]:
    st = load_settings()
    return list(st.get("saved_accounts", []))


def clear_all_saved_passwords() -> None:
    for name in list_saved_accounts():
        try:
            keyring.delete_password(APP_NAME, name)
        except Exception:
            pass
    st = load_settings()
    st["saved_accounts"] = []
    save_settings(st)


def open_settings_folder() -> None:
    # Best-effort OS open of the settings directory
    path = get_app_dir()
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except Exception:
        import webbrowser
        webbrowser.open(path.as_uri())


