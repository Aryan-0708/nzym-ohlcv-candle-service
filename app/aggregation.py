"""SQL-based OHLCV aggregation for raw market ticks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import Session

from app.models import Tick

BucketSize = Literal["1min", "daily"]
MINUTE_BUCKET_FORMAT = "%Y-%m-%dT%H:%M:00Z"
DAILY_BUCKET_FORMAT = "%Y-%m-%d"


@dataclass(frozen=True)
class Candle:
    """Aggregated OHLCV candle for a time bucket."""

    bucket: str
    open: float
    high: float
    low: float
    close: float
    volume: int


def get_1min_candles(
    session: Session,
    instrument_token: int,
    from_ts: datetime,
    to_ts: datetime,
) -> list[Candle]:
    """Return 1-minute candles for one instrument and timestamp range."""

    return _get_candles(
        session=session,
        bucket_size="1min",
        instrument_token=instrument_token,
        from_ts=from_ts,
        to_ts=to_ts,
    )


def get_daily_candles(
    session: Session,
    instrument_token: int,
    from_ts: datetime,
    to_ts: datetime,
) -> list[Candle]:
    """Return daily candles for one instrument and timestamp range."""

    return _get_candles(
        session=session,
        bucket_size="daily",
        instrument_token=instrument_token,
        from_ts=from_ts,
        to_ts=to_ts,
    )


def _get_candles(
    session: Session,
    bucket_size: BucketSize,
    instrument_token: int,
    from_ts: datetime,
    to_ts: datetime,
) -> list[Candle]:
    bucket = _bucket_expression(bucket_size)
    from_boundary = _as_utc_naive(from_ts)
    to_boundary = _as_utc_naive(to_ts)

    bucketed_ticks = (
        select(
            Tick.id.label("tick_id"),
            bucket.label("bucket"),
            Tick.ts.label("ts"),
            Tick.last_price.label("last_price"),
            Tick.volume.label("volume"),
        )
        .where(
            Tick.instrument_token == instrument_token,
            Tick.ts >= from_boundary,
            Tick.ts <= to_boundary,
        )
        .cte("bucketed_ticks")
    )

    ranked_ticks = (
        select(
            bucketed_ticks.c.bucket,
            bucketed_ticks.c.last_price,
            bucketed_ticks.c.volume,
            func.row_number()
            .over(
                partition_by=bucketed_ticks.c.bucket,
                order_by=(bucketed_ticks.c.ts.asc(), bucketed_ticks.c.tick_id.asc()),
            )
            .label("earliest_rank"),
            func.row_number()
            .over(
                partition_by=bucketed_ticks.c.bucket,
                order_by=(bucketed_ticks.c.ts.desc(), bucketed_ticks.c.tick_id.desc()),
            )
            .label("latest_rank"),
        )
        .cte("ranked_ticks")
    )

    candle_query = (
        select(
            ranked_ticks.c.bucket.label("bucket"),
            func.max(
                case(
                    (ranked_ticks.c.earliest_rank == 1, ranked_ticks.c.last_price),
                    else_=None,
                )
            )
            .label("open"),
            func.max(ranked_ticks.c.last_price).label("high"),
            func.min(ranked_ticks.c.last_price).label("low"),
            func.max(
                case(
                    (ranked_ticks.c.latest_rank == 1, ranked_ticks.c.last_price),
                    else_=None,
                )
            )
            .label("close"),
            (func.max(ranked_ticks.c.volume) - func.min(ranked_ticks.c.volume))
            .label("volume"),
        )
        .group_by(ranked_ticks.c.bucket)
        .order_by(ranked_ticks.c.bucket.asc())
    )

    return [
        Candle(
            bucket=str(row["bucket"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
        )
        for row in session.execute(candle_query).mappings()
    ]


def _bucket_expression(bucket_size: BucketSize) -> ColumnElement[str]:
    if bucket_size == "1min":
        return func.strftime(MINUTE_BUCKET_FORMAT, Tick.ts)

    return func.strftime(DAILY_BUCKET_FORMAT, Tick.ts)


def _as_utc_naive(value: datetime) -> datetime:
    """Match SQLite's stored UTC-naive datetime representation."""

    if value.tzinfo is None:
        return value

    return value.astimezone(UTC).replace(tzinfo=None)
