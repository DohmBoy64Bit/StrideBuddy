from __future__ import annotations

from pathlib import Path


def asset_path(name: str) -> str:
    """Return absolute path to an asset within the package assets directory."""
    return str(Path(__file__).resolve().parent / "assets" / name)


