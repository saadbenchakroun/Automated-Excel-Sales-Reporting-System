"""Cleaning pipeline: repairs and normalizes raw sales data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.constants import (
    CANCELLED_STATUSES,
    CANONICAL_CATEGORIES,
    CANONICAL_REGIONS,
    NUMERIC_COLUMNS,
    REGION_ALIASES,
    TEXT_COLUMNS,
    VALID_ORDER_STATUSES,
)
from src.dates import is_datetime_like, parse_series
from src.models import CleaningReport

PLACEHOLDER_CUSTOMER = "Unknown Customer"


def normalize_category(value: object) -> str:
    """Return the canonical category name for *value*."""
    text = str(value).strip()
    key = text.lower()
    if key in CANONICAL_CATEGORIES:
        return CANONICAL_CATEGORIES[key]
    return text.title()


def normalize_region(value: object) -> str:
    """Return the canonical region name for *value*."""
    text = str(value).strip()
    key = text.lower()
    key_compact = key.replace(" ", "").replace("-", "_")
    if key in CANONICAL_REGIONS:
        return CANONICAL_REGIONS[key]
    if key_compact in CANONICAL_REGIONS:
        return CANONICAL_REGIONS[key_compact]
    if key in REGION_ALIASES:
        return REGION_ALIASES[key]
    return text.title()


def normalize_capitalization(value: object) -> str:
    """Title-case a free text field such as a name or payment method."""
    text = str(value).strip()
    return text.title()


def _normalize_dates(series: pd.Series) -> pd.Series:
    """Parse mixed date representations into datetime values."""
    return parse_series(series)


def clean_dataframe(frame: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Apply the full cleaning pipeline to a raw DataFrame.

    Returns ``(cleaned, report)`` where *cleaned* contains only rows that pass
    validation and *report* describes exactly what was changed.
    """
    report = CleaningReport()
    report.rows_before = len(frame)
    df = frame.copy()

    # 1. Remove exact duplicate rows.
    before_dup = len(df)
    df = df.drop_duplicates(keep="first")
    report.duplicate_rows_removed = before_dup - len(df)
    report.rows_after_duplicates = len(df)

    # 2. Trim whitespace from all text columns.
    trimmed = 0
    for col in TEXT_COLUMNS:
        if col in df.columns:
            cleaned = df[col].astype(str).str.strip()
            trimmed += int((cleaned != df[col].astype(str)).sum())
            df[col] = cleaned.replace({"": None, "nan": None, "None": None})
    report.whitespace_trimmed_cells = trimmed

    # 3. Normalize dates.
    if "Order Date" in df.columns:
        raw_dates = df["Order Date"].astype(object)
        normalized = _normalize_dates(raw_dates)
        was_datetime = raw_dates.map(is_datetime_like)
        report.dates_normalized = int((~was_datetime & normalized.notna()).sum())
        df["Order Date"] = normalized

    # 4. Coerce numeric columns; non-numeric values become NaN.
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. Fill missing discounts with 0.
    if "Discount" in df.columns:
        report.missing_discounts_filled = int(df["Discount"].isna().sum())
        df["Discount"] = df["Discount"].fillna(0.0).clip(lower=0.0)
    else:
        df["Discount"] = 0.0

    # 6. Fill missing customer names.
    if "Customer Name" in df.columns:
        report.missing_customer_names_filled = int(
            df["Customer Name"].isna().sum()
            | df["Customer Name"].astype(str).str.strip().eq("").sum()
        )
        df["Customer Name"] = df["Customer Name"].fillna(PLACEHOLDER_CUSTOMER)
        df["Customer Name"] = df["Customer Name"].astype(str).str.strip().replace("", PLACEHOLDER_CUSTOMER)
    else:
        df["Customer Name"] = PLACEHOLDER_CUSTOMER
        report.missing_customer_names_filled = len(df)

    # 7. Normalize categorical attributes.
    df["Category"] = df["Category"].map(normalize_category)
    df["Region"] = df["Region"].map(normalize_region)
    for col in ("Customer Name", "Product Name", "Salesperson", "Payment Method"):
        if col in df.columns:
            df[col] = df[col].map(normalize_capitalization)

    # 8. Decide validity per row.
    valid_mask = pd.Series(True, index=df.index)
    if "Order Date" in df.columns:
        valid_mask &= df["Order Date"].notna()
    if "Quantity" in df.columns:
        valid_mask &= df["Quantity"].notna() & (df["Quantity"] > 0)
    if "Unit Price" in df.columns:
        valid_mask &= df["Unit Price"].notna() & (df["Unit Price"] >= 0)
    if "Order Status" in df.columns:
        valid_mask &= df["Order Status"].isin(VALID_ORDER_STATUSES)

    invalid = ~valid_mask
    report.invalid_rows_removed = int(invalid.sum())

    df_valid = df[valid_mask].copy()

    # 9. Calculated fields.
    df_valid["Gross Revenue"] = df_valid["Quantity"] * df_valid["Unit Price"]
    df_valid["Discount Amount"] = df_valid["Gross Revenue"] * df_valid["Discount"]
    df_valid["Net Revenue"] = df_valid["Gross Revenue"] - df_valid["Discount Amount"]

    # 10. Keep cancelled orders for reporting transparency.
    report.cancelled_rows_kept = int(df_valid["Order Status"].isin(CANCELLED_STATUSES).sum())

    report.rows_final = len(df_valid)
    return df_valid, report


def revenue_eligible(df: pd.DataFrame) -> pd.DataFrame:
    """Return only the rows that count towards revenue (excludes cancelled/refunded)."""
    return df[~df["Order Status"].isin(CANCELLED_STATUSES)]
