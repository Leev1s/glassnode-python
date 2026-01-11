"""Utility helpers shared across the package."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Mapping, MutableMapping, Sequence, Tuple, Union

import pandas as pd

TickerInput = Union[str, Sequence[str]]
DateInput = Union[str, datetime, None]

SUPPORTED_PERIOD_UNITS = {"d": 24 * 3600, "mo": 30 * 24 * 3600, "y": 365 * 24 * 3600}


class InvalidPeriod(ValueError):
    """Raised when a period string cannot be parsed."""


def normalize_tickers(value: TickerInput) -> List[str]:
    if isinstance(value, str):
        cleaned = value.strip().upper()
        return [cleaned]
    if not isinstance(value, Sequence):
        raise TypeError("tickers must be a string or a sequence of strings")
    tickers = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("ticker symbols must be strings")
        ticker = item.strip().upper()
        if ticker:
            tickers.append(ticker)
    if not tickers:
        raise ValueError("at least one ticker symbol is required")
    return tickers


def _to_datetime(value: DateInput) -> datetime:
    if value is None:
        raise ValueError("datetime value is required")
    if isinstance(value, datetime):
        dt = value
    else:
        dt = pd.to_datetime(value).to_pydatetime()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def period_to_seconds(period: str) -> int:
    text = (period or "").strip().lower()
    if not text:
        raise InvalidPeriod("period cannot be empty")
    if text.endswith("mo"):
        multiplier = SUPPORTED_PERIOD_UNITS["mo"]
        number = text[:-2]
    elif text.endswith("y"):
        multiplier = SUPPORTED_PERIOD_UNITS["y"]
        number = text[:-1]
    elif text.endswith("d"):
        multiplier = SUPPORTED_PERIOD_UNITS["d"]
        number = text[:-1]
    else:
        raise InvalidPeriod(
            "supported suffixes are 'd', 'mo', and 'y' (e.g. 7d, 3mo, 1y)"
        )
    if not number.isdigit():
        raise InvalidPeriod("period prefix must be a positive integer")
    return int(number) * multiplier


def compute_time_range(
    start: DateInput = None,
    end: DateInput = None,
    period: str = "1mo",
) -> Tuple[int, int]:
    end_dt = _to_datetime(end) if end else datetime.now(timezone.utc)
    if start:
        start_dt = _to_datetime(start)
    else:
        seconds = period_to_seconds(period)
        start_dt = end_dt - timedelta(seconds=seconds)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


_OHLC_FIELD_MAP = {"o": "open", "h": "high", "l": "low", "c": "close"}


def parse_series(items: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    data = list(items)
    if not data:
        return pd.DataFrame()

    rows = []
    for entry in data:
        ts = entry.get("t")
        if ts is None:
            continue

        base: MutableMapping[str, Any] = {"date": pd.to_datetime(ts, unit="s", utc=True)}
        ohlc = entry.get("o")
        if isinstance(ohlc, Mapping):
            base.update({name: ohlc.get(code) for code, name in _OHLC_FIELD_MAP.items()})
        elif "v" in entry:
            base["value"] = entry.get("v")
        else:
            for key, value in entry.items():
                if key == "t":
                    continue
                base[key] = value

        rows.append(base)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.set_index("date").sort_index()

def endpoint_to_column_name(endpoint: str) -> str:
    """Convert the last path fragment of an endpoint into a CamelCase column name."""
    slug = (endpoint or "").strip("/").split("/")[-1]
    if not slug:
        return "Metric"
    parts = [part for part in slug.split("_") if part]
    return "".join(part.capitalize() for part in parts) or "Metric"
