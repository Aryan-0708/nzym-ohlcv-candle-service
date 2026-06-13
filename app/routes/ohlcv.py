"""OHLCV candle routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas import ErrorResponse, OHLCVCandle
from app.services.candle_service import (
    get_daily_ohlcv_candles,
    get_one_minute_candles,
)

router = APIRouter(prefix="/ohlcv", tags=["ohlcv"])


def get_db_session():
    """Yield a database session for one request."""

    with SessionLocal() as session:
        yield session


@router.get(
    "/1min",
    response_model=list[OHLCVCandle],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def one_minute_candles(
    instrument_token: Annotated[int, Query(gt=0)],
    from_ts: Annotated[datetime, Query(alias="from")],
    to_ts: Annotated[datetime, Query(alias="to")],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[OHLCVCandle]:
    """Return 1-minute OHLCV candles."""

    candles = get_one_minute_candles(session, instrument_token, from_ts, to_ts)
    return [OHLCVCandle.model_validate(candle, from_attributes=True) for candle in candles]


@router.get(
    "/daily",
    response_model=list[OHLCVCandle],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def daily_candles(
    instrument_token: Annotated[int, Query(gt=0)],
    from_ts: Annotated[datetime, Query(alias="from")],
    to_ts: Annotated[datetime, Query(alias="to")],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[OHLCVCandle]:
    """Return daily OHLCV candles."""

    candles = get_daily_ohlcv_candles(session, instrument_token, from_ts, to_ts)
    return [OHLCVCandle.model_validate(candle, from_attributes=True) for candle in candles]

