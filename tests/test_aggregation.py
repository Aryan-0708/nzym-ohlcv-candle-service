from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.aggregation import get_1min_candles
from app.database import Base
from app.models import Tick


@pytest.fixture()
def session(tmp_path) -> Session:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'aggregation.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db_session:
        yield db_session

    engine.dispose()


def test_1min_candle_uses_sql_ohlcv_and_timestamp_order(session: Session) -> None:
    instrument_token = 101

    session.add_all(
        [
            Tick(
                instrument_token=instrument_token,
                ts=datetime(2026, 6, 9, 9, 15, 20),
                last_price=105,
                volume=1200,
            ),
            Tick(
                instrument_token=instrument_token,
                ts=datetime(2026, 6, 9, 9, 15, 1),
                last_price=100,
                volume=1000,
            ),
            Tick(
                instrument_token=instrument_token,
                ts=datetime(2026, 6, 9, 9, 15, 59),
                last_price=103,
                volume=1500,
            ),
            Tick(
                instrument_token=instrument_token,
                ts=datetime(2026, 6, 9, 9, 15, 40),
                last_price=99,
                volume=1300,
            ),
        ]
    )
    session.commit()

    candles = get_1min_candles(
        session=session,
        instrument_token=instrument_token,
        from_ts=datetime(2026, 6, 9, 9, 15),
        to_ts=datetime(2026, 6, 9, 9, 16),
    )

    assert len(candles) == 1
    assert candles[0].bucket == "2026-06-09T09:15:00Z"
    assert candles[0].open == 100
    assert candles[0].high == 105
    assert candles[0].low == 99
    assert candles[0].close == 103
    assert candles[0].volume == 500


def test_single_tick_bucket_returns_zero_volume(session: Session) -> None:
    instrument_token = 202
    tick_ts = datetime(2026, 6, 9, 9, 15, 1)

    session.add(
        Tick(
            instrument_token=instrument_token,
            ts=tick_ts,
            last_price=100,
            volume=1000,
        )
    )
    session.commit()

    candles = get_1min_candles(
        session=session,
        instrument_token=instrument_token,
        from_ts=tick_ts,
        to_ts=tick_ts,
    )

    assert candles[0].open == 100
    assert candles[0].high == 100
    assert candles[0].low == 100
    assert candles[0].close == 100
    assert candles[0].volume == 0

