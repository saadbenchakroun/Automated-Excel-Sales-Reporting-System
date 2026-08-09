"""Robust date parsing for mixed input formats.

Business Excel files rarely use a single date format. This module tries an
ordered list of explicit formats (day-first representations first, since those
are the most common source of ``%d/%m/%Y`` entries in imported CSV/Excel data),
then falls back to pandas' ISO/UTC inference.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

# Ordered attempts. Day-first slash/dot formats come first because a trailing
# "%m/%d/%Y" attempt would otherwise swallow them as month/day.
STRPTIME_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
]


def is_datetime_like(value: object) -> bool:
    """True if *value* is already a datetime/timestamp object."""
    return isinstance(value, pd.Timestamp) or hasattr(value, "year")


def parse_datetime(value: object) -> pd.Timestamp | None:
    """Parse a single value into a ``pd.Timestamp`` or return ``None``.

    ``None`` is returned for empty, null or unparseable values.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value
    if hasattr(value, "year"):  # datetime.date / datetime.datetime
        return pd.Timestamp(value)

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "na"}:
        return None

    for fmt in STRPTIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            return pd.Timestamp(parsed)
        except ValueError:
            continue

    # Final fallback: ISO-like ("2026-01-15", "2026.01.15", "2026/01/15", timestamps).
    try:
        parsed = pd.to_datetime(text, format="ISO8601", errors="raise")
        return pd.Timestamp(parsed)
    except (ValueError, TypeError):
        return None


def parse_series(series: pd.Series) -> pd.Series:
    """Parse a Series of mixed date representations into ``datetime64`` values."""
    parsed = series.map(parse_datetime)
    return pd.to_datetime(parsed, errors="coerce")
