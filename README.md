# Nzym OHLCV Candle Service

FastAPI service for loading raw market ticks from `ticks.jsonl`, storing them in SQLite, and serving 1-minute and daily OHLCV candles.

Aggregation is done in SQL using SQLAlchemy expressions and SQLite window functions. The service does not pull every tick into Python and loop to aggregate candles.

## Features

- Tick loader for JSON Lines input
- SQLite storage
- 1-minute OHLCV candles
- Daily OHLCV candles
- Out-of-order tick handling using timestamp ordering
- Correct conversion from cumulative feed volume to traded candle volume
- FastAPI endpoints
- Pytest coverage for aggregation and API behavior
- Docker support

## Architecture

```text
ticks.jsonl -> loader -> SQLite -> SQL aggregation -> service layer -> API
```

The loader persists raw ticks. API requests flow through thin FastAPI route handlers into a service layer, which validates inputs and calls the SQL aggregation functions.

## Data Model

The `ticks` table stores raw feed ticks:

- `id`
- `instrument_token`
- `ts`
- `last_price`
- `volume`

Indexes are defined on `instrument_token`, `ts`, and `(instrument_token, ts)` so instrument/range scans used by candle queries are efficient.

## OHLCV Logic

For each bucket:

- `open` = price at the earliest timestamp in the bucket
- `high` = maximum price in the bucket
- `low` = minimum price in the bucket
- `close` = price at the latest timestamp in the bucket

Open and close are selected with SQL `ROW_NUMBER()` window functions ordered by timestamp. Insertion order is never used, so out-of-order ticks still produce correct candles.

## Volume Logic

The feed volume is cumulative for the trading day, not per tick.

Example cumulative volumes inside one bucket:

```text
1000, 1200, 1500
```

The candle's traded volume is:

```text
max(volume) - min(volume) = 1500 - 1000 = 500
```

## API Endpoints

### `GET /health`

Example:

```bash
curl http://localhost:8000/health
```

Response:

```json
{"status":"ok"}
```

### `GET /ohlcv/1min?instrument_token=&from=&to=`

Example:

```bash
curl "http://localhost:8000/ohlcv/1min?instrument_token=408065&from=2026-06-09T09:15:00Z&to=2026-06-09T09:20:00Z"
```

Response:

```json
[
  {
    "bucket": "2026-06-09T09:15:00Z",
    "open": 1525.06,
    "high": 1525.06,
    "low": 1523.14,
    "close": 1523.14,
    "volume": 5743
  }
]
```

### `GET /ohlcv/daily?instrument_token=&from=&to=`

Example:

```bash
curl "http://localhost:8000/ohlcv/daily?instrument_token=408065&from=2026-06-09T00:00:00Z&to=2026-06-10T00:00:00Z"
```

Response:

```json
[
  {
    "bucket": "2026-06-09",
    "open": 1525.06,
    "high": 1697.92,
    "low": 1476.3,
    "close": 1658.23,
    "volume": 6066655
  }
]
```

## Run Locally

Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Load ticks into SQLite:

```powershell
python -m app.loader
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

Open the interactive docs:

```text
http://localhost:8000/docs
```

The app also initializes SQLite on startup. If the database is empty and `ticks.jsonl` is present, it loads the sample ticks automatically.

## Run Tests

```powershell
pytest -q
```

Expected result:

```text
7 passed
```

Tests use isolated SQLite databases and deterministic in-test data. They do not depend on `ticks.jsonl`.

## Docker

Run the service from a clean clone:

```bash
docker compose up
```

Then open:

```text
http://localhost:8000/docs
```

The container creates the SQLite schema on startup and loads `ticks.jsonl` automatically if the database is empty.

## Design Tradeoff

SQLite is used instead of Postgres for this assessment because it keeps setup simple, is sufficient for the provided dataset size, and makes the project reproducible from a clean clone with no extra database container. SQLite also supports the SQL features needed here, including CTEs and window functions, so the core aggregation requirement is still handled in the database.
