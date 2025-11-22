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
        }
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "last_screen_name": "",
            "save_password": False,
            "auto_login": False,
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


def delete_saved_password(screen_name: str) -> None:
    if not screen_name:
        return
    try:
        keyring.delete_password(APP_NAME, screen_name)
    except keyring.errors.PasswordDeleteError:
        pass


