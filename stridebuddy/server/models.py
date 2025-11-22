from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    screen_name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    reset_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reset_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Buddy(Base):
    __tablename__ = "buddies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_screen_name: Mapped[str] = mapped_column(String(32), index=True)
    buddy_screen_name: Mapped[str] = mapped_column(String(32), index=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


