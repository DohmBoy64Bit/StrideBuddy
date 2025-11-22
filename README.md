# StrideBuddy (AIM‑inspired messenger)

StrideBuddy is a nostalgic instant messenger inspired by the AIM 5.x era — rebuilt with Python + PySide6 and a tiny Flask backend. It includes a faithful sign‑on UI, a buddy list, message windows with formatting, presence, and a modern settings dialog.

## Screenshot

<p align="center">
  <img src="https://i.imgur.com/WZcoQCx.png" width="300">
</p>

## Features
- Classic sign‑on with Save password and Auto‑login (OS keychain)
- Buddy List with groups, add/remove, per‑buddy mute/block, presence (online/away/offline)
- Chat windows with bold/italic/underline, color, links, emoji, sounds, transcript logging
- Typing indicators, tray toasts, and a lightweight server for auth/presence/messaging
- Setup dialog with Account, Connection, Notifications, Chat, Appearance, Privacy, Data, About

## Quick start
1) Create a venv (optional)
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2) Install dependencies
```bash
pip install -r requirements.txt
```

3) Start the server (terminal 1)
```bash
python -m stridebuddy.server
```
By default it serves at `http://127.0.0.1:5000`.

4) Launch the desktop client (terminal 2)
```bash
python -m stridebuddy
```
Use “Get a Screen Name” to create an account, then sign in.

## How it works
- The client keeps a persistent login session (cookie) and uses it for presence, buddies, and messaging.
- Presence derives online/away/offline from recent heartbeats and idle activity.
- Messages deliver plain text plus HTML; the receiver renders HTML if present.
- Buddies are validated on the server; mute/block flags and group names persist.

## Troubleshooting
- Sounds: Enable in Setup → Notifications; ensure system audio isn’t muted.
- Logs: Enable “Enable transcript logging” in Setup → Chat. Logs write to `%APPDATA%\StrideBuddy\logs`.
- 401 Unauthorized: Session expired — sign out and sign in again.
- Help/Signup 404: Restart the server and hard‑refresh the page (Ctrl+F5).

## Roadmap
- Drag/drop group reordering and richer group management
- File/image sharing
- Optional encryption and improved auth/session security
- Packaging for Windows and cross‑platform builds

Tested on Windows 10/11 with Python 3.10+. PRs welcome!
