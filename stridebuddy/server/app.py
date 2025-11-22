from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from passlib.hash import bcrypt
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import secrets
import time

from .models import Base, User, Buddy


def get_db_url() -> str:
    data_dir = Path(os.getenv("SB_DATA_DIR", ".")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'stridebuddy.db'}"


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = os.getenv("SB_SECRET", "stridebuddy-dev-secret")

    engine = create_engine(get_db_url(), future=True)
    Base.metadata.create_all(engine)
    _ensure_optional_columns(engine)
    _ensure_buddy_table(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    # In-memory presence and message queues (dev prototype)
    ONLINE: dict[str, datetime] = {}
    MESSAGE_QUEUES: dict[str, list[dict]] = {}

    @app.get("/")
    def root() -> Tuple[str, int] | str:
        return redirect(url_for("signup"))

    @app.get("/favicon.ico")
    def favicon():
        # Reuse runner.svg as favicon to avoid 404 noise
        return app.send_static_file("runner.svg")

    @app.get("/signup")
    def signup() -> str:
        return render_template("signup.html")

    @app.get("/forgot")
    def forgot() -> str:
        return render_template("forgot.html")

    @app.route("/help", methods=["GET"], strict_slashes=False)
    def help_page() -> str:
        return render_template("help.html")

    # --- Presence & Messaging (prototype) ---
    @app.post("/api/presence/heartbeat")
    def presence_heartbeat():
        user = session.get("user")
        if not user:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        ONLINE[user] = datetime.utcnow()
        return jsonify({"ok": True})

    @app.get("/api/presence/online")
    def presence_online():
        now = datetime.utcnow()
        online = [name for name, ts in ONLINE.items() if (now - ts) < timedelta(seconds=15)]
        return jsonify({"ok": True, "online": online})

    @app.post("/api/messages/send")
    def send_message():
        user = session.get("user")
        if not user:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        sender = user
        to = (data.get("to") or "").strip()
        content = (data.get("content") or "").strip()
        content_html = (data.get("content_html") or "").strip()
        if not to or not content:
            return jsonify({"ok": False, "error": "to and content required"}), 400
        msg = {
            "from": sender,
            "to": to,
            "content": content,
            "content_html": content_html,
            "ts": datetime.utcnow().isoformat(),
        }
        MESSAGE_QUEUES.setdefault(to, []).append(msg)
        return jsonify({"ok": True})

    @app.get("/api/messages/poll")
    def poll_messages():
        screen_name = session.get("user")
        if not screen_name:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        timeout = int(request.args.get("timeout", "15"))
        deadline = time.time() + min(timeout, 30)
        while time.time() < deadline:
            queue = MESSAGE_QUEUES.get(screen_name, [])
            if queue:
                out = queue.copy()
                MESSAGE_QUEUES[screen_name] = []
                return jsonify({"ok": True, "messages": out})
            time.sleep(0.4)
        return jsonify({"ok": True, "messages": []})

    # --- Buddies API ---
    @app.get("/api/buddies")
    def list_buddies():
        owner = session.get("user")
        if not owner:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        with SessionLocal() as db:
            rows = db.query(Buddy).filter(Buddy.owner_screen_name == owner).all()
            data = [{"buddy": b.buddy_screen_name, "group": b.group_name or ""} for b in rows]
        return jsonify({"ok": True, "buddies": data})

    @app.post("/api/buddies")
    def add_buddy():
        owner = session.get("user")
        if not owner:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        buddy = (data.get("buddy") or "").strip()
        group = (data.get("group") or "").strip() or None
        if not buddy:
            return jsonify({"ok": False, "error": "buddy required"}), 400
        if buddy == owner:
            return jsonify({"ok": False, "error": "cannot add yourself"}), 400
        with SessionLocal() as db:
            target = db.scalar(select(User).where(User.screen_name == buddy))
            if not target:
                return jsonify({"ok": False, "error": "user not found"}), 404
            exists = db.scalar(select(Buddy).where(Buddy.owner_screen_name == owner, Buddy.buddy_screen_name == buddy))
            if exists:
                return jsonify({"ok": True})
            db.add(Buddy(owner_screen_name=owner, buddy_screen_name=buddy, group_name=group))
            db.commit()
        return jsonify({"ok": True})

    @app.delete("/api/buddies")
    def delete_buddy():
        owner = session.get("user")
        if not owner:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        buddy = (data.get("buddy") or "").strip()
        if not buddy:
            return jsonify({"ok": False, "error": "buddy required"}), 400
        with SessionLocal() as db:
            db.query(Buddy).filter(Buddy.owner_screen_name == owner, Buddy.buddy_screen_name == buddy).delete()
            db.commit()
        return jsonify({"ok": True})

    @app.post("/api/auth/signup")
    def api_signup():
        data = request.get_json(silent=True) or {}
        screen_name = (data.get("screen_name") or "").strip()
        password = (data.get("password") or "").strip()
        if not screen_name or not password:
            return jsonify({"ok": False, "error": "screen_name and password required"}), 400
        if len(screen_name) < 2 or len(screen_name) > 32:
            return jsonify({"ok": False, "error": "screen_name must be 2-32 chars"}), 400
        pw_hash = bcrypt.hash(password)
        with SessionLocal() as db:
            exists = db.scalar(select(User).where(User.screen_name == screen_name))
            if exists:
                return jsonify({"ok": False, "error": "screen_name already taken"}), 409
            user = User(screen_name=screen_name, password_hash=pw_hash)
            db.add(user)
            db.commit()
        return jsonify({"ok": True})

    @app.post("/api/auth/login")
    def api_login():
        data = request.get_json(silent=True) or {}
        screen_name = (data.get("screen_name") or "").strip()
        password = (data.get("password") or "").strip()
        if not screen_name or not password:
            return jsonify({"ok": False, "error": "screen_name and password required"}), 400
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.screen_name == screen_name))
            if not user or not bcrypt.verify(password, user.password_hash):
                return jsonify({"ok": False, "error": "invalid credentials"}), 401
        # Set session cookie
        session["user"] = screen_name
        return jsonify({"ok": True})

    @app.post("/api/auth/request_reset")
    def api_request_reset():
        data = request.get_json(silent=True) or {}
        screen_name = (data.get("screen_name") or "").strip()
        if not screen_name:
            return jsonify({"ok": False, "error": "screen_name required"}), 400
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.screen_name == screen_name))
            if not user:
                return jsonify({"ok": True})  # don't reveal existence
            code = f"{secrets.randbelow(1000000):06d}"
            user.reset_code = code
            user.reset_expires_at = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
            # In dev, return the code so you can test without email
            return jsonify({"ok": True, "dev_code": code})

    @app.post("/api/auth/reset")
    def api_reset():
        data = request.get_json(silent=True) or {}
        screen_name = (data.get("screen_name") or "").strip()
        code = (data.get("code") or "").strip()
        new_password = (data.get("new_password") or "").strip()
        if not all([screen_name, code, new_password]):
            return jsonify({"ok": False, "error": "screen_name, code, new_password required"}), 400
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.screen_name == screen_name))
            if not user or not user.reset_code or user.reset_code != code:
                return jsonify({"ok": False, "error": "invalid code"}), 400
            if user.reset_expires_at and user.reset_expires_at < datetime.utcnow():
                return jsonify({"ok": False, "error": "code expired"}), 400
            user.password_hash = bcrypt.hash(new_password)
            user.reset_code = None
            user.reset_expires_at = None
            db.commit()
        return jsonify({"ok": True})

    return app


def main() -> None:
    app = create_app()
    port = int(os.getenv("SB_PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()

def _ensure_optional_columns(engine) -> None:
    # Tiny migration helper: add reset columns if they don't exist.
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()}
        if "reset_code" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_code VARCHAR(32)"))
        if "reset_expires_at" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_expires_at DATETIME"))

def _ensure_buddy_table(engine) -> None:
    with engine.begin() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        if "buddies" not in tables:
            conn.execute(text("""
                CREATE TABLE buddies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_screen_name VARCHAR(32) NOT NULL,
                    buddy_screen_name VARCHAR(32) NOT NULL,
                    group_name VARCHAR(64)
                )
            """))


