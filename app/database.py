"""Database configuration for the Nzym OHLCV candle service."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = f"sqlite:///{Path('nzym_ohlcv.db')}"


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def create_db() -> None:
    """Create database tables for all registered models."""

    Base.metadata.create_all(bind=engine)

