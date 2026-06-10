# Take-home: OHLCV candle service

**Time box:** 1 day. We care about judgment and clean execution over completeness. If you run out of time, write down what you'd do next.

## Context

We turn raw market ticks into aggregated OHLCV candles and serve them over an API. This exercise is a miniature of that pipeline — no broker accounts or cloud access required.

## What you're given

`ticks.jsonl` — one JSON tick per line:

```json
{"instrument_token": 408065, "ts": "2026-06-09T09:15:00.142Z", "last_price": 1523.45, "volume": 1820345}
```

Two things to note about the data:

- `volume` is the **cumulative total for the trading day** (as real feeds report it), not a per-tick amount.
- Ticks are **not guaranteed to be in timestamp order** — some arrive slightly late, exactly as they would over a real network.

## What to build

1. **Loader** — read `ticks.jsonl` and store the ticks. SQLite or Postgres, your call.
2. **API** — a FastAPI service exposing:
   - `GET /ohlcv/1min?instrument_token=&from=&to=` → 1-minute candles `{bucket, open, high, low, close, volume}` for the range.
   - `GET /ohlcv/daily?instrument_token=&from=&to=` → daily candles, same shape with a `date` bucket.
   - `GET /health`
   - Candle `volume` is the **traded volume within that bucket** — derive it from the cumulative figure correctly.
3. **Out-of-order handling** — your candles must be correct regardless of the order ticks arrive in.
4. **Docker** — `docker compose up` brings up the service (and DB, if you use one). Run instructions in the README.
5. **Tests** — cover the aggregation logic and at least one failure path (e.g. unknown instrument, invalid date range). No assertions on the status code alone; assert on the actual candle values.
6. **README** — how to run, how to test, and 3–4 lines on your data model and the one design tradeoff you most want to defend.

## Constraints

- Python 3.11+.
- Keep config and secrets out of code.
- Don't pull every row into Python and loop to aggregate — express the aggregation where it belongs.

## Submission

A public GitHub repo containing the code, the test suite, the Docker setup, and the README. Incremental commits are preferred over a single final dump.
