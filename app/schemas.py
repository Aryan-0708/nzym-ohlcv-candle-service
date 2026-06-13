"""Pydantic schemas for API responses."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str


class OHLCVCandle(BaseModel):
    """OHLCV candle returned by the API."""

    bucket: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ErrorResponse(BaseModel):
    """Error response returned by API handlers."""

    message: str

