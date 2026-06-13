"""Service layer for OHLCV candle retrieval."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aggregation import Candle, get_1min_candles, get_daily_candles
from app.models import Tick


class CandleServiceError(Exception):
    """Base exception for candle service errors."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidDateRangeError(CandleServiceError):
    """Raised when a requested timestamp range is invalid."""

    status_code = 400


class UnknownInstrumentError(CandleServiceError):
    """Raised when no ticks exist for an instrument."""

    status_code = 404


def get_one_minute_candles(
    session: Session,
    instrument_token: int,
    from_ts: datetime,
    to_ts: datetime,
) -> list[Candle]:
    """Return 1-minute candles after validating the request."""

    _validate_request(session, instrument_token, from_ts, to_ts)
    return get_1min_candles(session, instrument_token, from_ts, to_ts)


def get_daily_ohlcv_candles(
    session: Session,
    instrument_token: int,
    from_ts: datetime,
    to_ts: datetime,
) -> list[Candle]:
    """Return daily candles after validating the request."""

    _validate_request(session, instrument_token, from_ts, to_ts)
    return get_daily_candles(session, instrument_token, from_ts, to_ts)


def _validate_request(
    session: Session,
    instrument_token: int,
    from_ts: datetime,
    to_ts: datetime,
) -> None:
    if from_ts > to_ts:
        raise InvalidDateRangeError("'from' timestamp must be before or equal to 'to'.")

    if not _instrument_exists(session, instrument_token):
        raise UnknownInstrumentError(
            f"No ticks found for instrument_token={instrument_token}."
        )


def _instrument_exists(session: Session, instrument_token: int) -> bool:
    statement = (
        select(Tick.id)
        .where(Tick.instrument_token == instrument_token)
        .limit(1)
    )
    return session.execute(statement).scalar_one_or_none() is not None

