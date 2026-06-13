from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app
from app.models import Tick
from app.routes.ohlcv import get_db_session


@pytest.fixture()
def api_app(tmp_path) -> FastAPI:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        session.add_all(
            [
                Tick(
                    instrument_token=101,
                    ts=datetime(2026, 6, 9, 9, 15, 20),
                    last_price=105,
                    volume=1200,
                ),
                Tick(
                    instrument_token=101,
                    ts=datetime(2026, 6, 9, 9, 15, 1),
                    last_price=100,
                    volume=1000,
                ),
                Tick(
                    instrument_token=101,
                    ts=datetime(2026, 6, 9, 9, 15, 59),
                    last_price=103,
                    volume=1500,
                ),
                Tick(
                    instrument_token=101,
                    ts=datetime(2026, 6, 9, 9, 15, 40),
                    last_price=99,
                    volume=1300,
                ),
            ]
        )
        session.commit()

    def override_db_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session

    yield app

    app.dependency_overrides.clear()
    engine.dispose()


def test_health(api_app: FastAPI) -> None:
    response = get(api_app, "/health")

    assert response["status_code"] == 200
    assert response["json"] == {"status": "ok"}


def test_get_1min_candles(api_app: FastAPI) -> None:
    response = get(
        api_app,
        "/ohlcv/1min",
        {
            "instrument_token": "101",
            "from": "2026-06-09T09:15:00Z",
            "to": "2026-06-09T09:16:00Z",
        },
    )

    assert response["status_code"] == 200
    assert response["json"] == [
        {
            "bucket": "2026-06-09T09:15:00Z",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 500,
        }
    ]


def test_get_daily_candles(api_app: FastAPI) -> None:
    response = get(
        api_app,
        "/ohlcv/daily",
        {
            "instrument_token": "101",
            "from": "2026-06-09T00:00:00Z",
            "to": "2026-06-09T23:59:59Z",
        },
    )

    assert response["status_code"] == 200
    assert response["json"] == [
        {
            "bucket": "2026-06-09",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 500,
        }
    ]


def test_unknown_instrument_returns_error_body(api_app: FastAPI) -> None:
    response = get(
        api_app,
        "/ohlcv/1min",
        {
            "instrument_token": "999",
            "from": "2026-06-09T09:15:00Z",
            "to": "2026-06-09T09:16:00Z",
        },
    )

    assert response["status_code"] == 404
    assert response["json"] == {"message": "No ticks found for instrument_token=999."}


def test_invalid_date_range_returns_error_body(api_app: FastAPI) -> None:
    response = get(
        api_app,
        "/ohlcv/1min",
        {
            "instrument_token": "101",
            "from": "2026-06-10T00:00:00Z",
            "to": "2026-06-09T00:00:00Z",
        },
    )

    assert response["status_code"] == 400
    assert response["json"] == {
        "message": "'from' timestamp must be before or equal to 'to'."
    }


def get(
    test_app: FastAPI,
    path: str,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    return anyio.run(_get, test_app, path, params or {})


async def _get(
    test_app: FastAPI,
    path: str,
    params: dict[str, str],
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    request_sent = False

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": urlencode(params).encode("ascii"),
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, Any]:
        nonlocal request_sent

        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}

        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await test_app(scope, receive, send)

    start_message = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )

    return {
        "status_code": start_message["status"],
        "json": json.loads(body.decode("utf-8")),
    }

