"""SQLAlchemy models for persisted market ticks."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Tick(Base):
    """Raw market tick received for an instrument at a point in time."""

    __tablename__ = "ticks"
    __table_args__ = (
        Index("ix_ticks_instrument_token", "instrument_token"),
        Index("ix_ticks_ts", "ts"),
        Index("ix_ticks_instrument_token_ts", "instrument_token", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_token: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)

