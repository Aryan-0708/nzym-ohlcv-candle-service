"""Load raw tick data from JSON Lines into SQLite."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import insert

from app.database import SessionLocal, create_db
from app.models import Tick

DEFAULT_TICKS_PATH = Path("ticks.jsonl")
BATCH_SIZE = 1_000


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC."""

    normalized_value = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized_value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def parse_tick(raw_tick: dict[str, Any], line_number: int) -> dict[str, Any]:
    """Validate and convert a raw JSON tick into database-ready values."""

    try:
        return {
            "instrument_token": int(raw_tick["instrument_token"]),
            "ts": parse_timestamp(str(raw_tick["ts"])),
            "last_price": float(raw_tick["last_price"]),
            "volume": int(raw_tick["volume"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid tick on line {line_number}") from exc


def iter_ticks(path: Path) -> Iterable[dict[str, Any]]:
    """Yield parsed ticks from a JSON Lines file one line at a time."""

    with path.open("r", encoding="utf-8") as tick_file:
        for line_number, line in enumerate(tick_file, start=1):
            stripped_line = line.strip()
            if not stripped_line:
                continue

            try:
                raw_tick = json.loads(stripped_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}") from exc

            if not isinstance(raw_tick, dict):
                raise ValueError(f"Expected JSON object on line {line_number}")

            yield parse_tick(raw_tick, line_number)


def load_ticks(path: Path = DEFAULT_TICKS_PATH, batch_size: int = BATCH_SIZE) -> int:
    """Create the schema if needed and load ticks into the database."""

    create_db()

    loaded_count = 0
    batch: list[dict[str, Any]] = []

    with SessionLocal() as session:
        for tick in iter_ticks(path):
            batch.append(tick)

            if len(batch) >= batch_size:
                session.execute(insert(Tick), batch)
                session.commit()
                loaded_count += len(batch)
                batch.clear()

        if batch:
            session.execute(insert(Tick), batch)
            session.commit()
            loaded_count += len(batch)

    return loaded_count


def main() -> None:
    """CLI entry point for loading the default ticks file."""

    loaded_count = load_ticks()
    print(f"Loaded {loaded_count} rows.")


if __name__ == "__main__":
    main()

