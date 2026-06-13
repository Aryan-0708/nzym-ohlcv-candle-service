"""FastAPI application for the Nzym OHLCV candle service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.database import SessionLocal, create_db
from app.loader import DEFAULT_TICKS_PATH, load_ticks
from app.models import Tick
from app.routes.health import router as health_router
from app.routes.ohlcv import router as ohlcv_router
from app.schemas import ErrorResponse
from app.services.candle_service import CandleServiceError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the SQLite database before serving requests."""

    create_db()

    with SessionLocal() as session:
        tick_count = session.execute(select(func.count(Tick.id))).scalar_one()

    if tick_count == 0 and DEFAULT_TICKS_PATH.exists():
        loaded_count = load_ticks(DEFAULT_TICKS_PATH)
        print(f"Loaded {loaded_count} rows into SQLite.")

    yield


app = FastAPI(title="Nzym OHLCV Candle Service", lifespan=lifespan)


@app.exception_handler(CandleServiceError)
def candle_service_exception_handler(
    request: Request,
    exc: CandleServiceError,
) -> JSONResponse:
    """Return service-layer errors in the API error schema."""

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.message).model_dump(),
    )


@app.exception_handler(RequestValidationError)
def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return request validation errors in the API error schema."""

    first_error = exc.errors()[0]
    location = ".".join(str(part) for part in first_error["loc"])
    message = f"Invalid request parameter '{location}': {first_error['msg']}"

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(message=message).model_dump(),
    )


app.include_router(health_router)
app.include_router(ohlcv_router)
