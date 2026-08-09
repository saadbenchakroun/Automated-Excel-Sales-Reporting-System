"""Tests for the data cleaning pipeline."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_cleaner import (
    clean_dataframe,
    normalize_category,
    normalize_region,
    revenue_eligible,
)


def test_normalize_category_and_region():
    assert normalize_category("electronics ") == "Electronics"
    assert normalize_category("office equipment") == "Office Equipment"
    assert normalize_category("ELECTRONICS") == "Electronics"
    assert normalize_region("north america") == "North America"
    assert normalize_region("APAC") == "Asia Pacific"
    assert normalize_region("europe") == "Europe"
    assert normalize_region("South america") == "South America"


def test_duplicate_rows_removed(raw_df):
    cleaned, report = clean_dataframe(raw_df)
    assert report.duplicate_rows_removed == 1
    assert len(cleaned) == len(raw_df) - 1 - report.invalid_rows_removed


def test_whitespace_trimmed(raw_df):
    cleaned, report = clean_dataframe(raw_df)
    assert report.whitespace_trimmed_cells > 0
    assert not cleaned["Customer Name"].str.endswith(" ").any()
    assert "Daniel Kim" in cleaned["Salesperson"].values


def test_missing_discount_filled(raw_df):
    cleaned, report = clean_dataframe(raw_df)
    assert report.missing_discounts_filled == 1
    assert (cleaned["Discount"] >= 0).all()


def test_missing_customer_name_filled(raw_df):
    cleaned, report = clean_dataframe(raw_df)
    assert report.missing_customer_names_filled >= 1
    assert not cleaned["Customer Name"].astype(str).str.strip().eq("").any()


def test_invalid_rows_removed(raw_df):
    cleaned, report = clean_dataframe(raw_df)
    # raw_df contains one invalid row (negative quantity) -> removed.
    assert report.invalid_rows_removed == 1
    assert "NS-2026-00005" not in cleaned["Order ID"].values


def test_cancelled_rows_kept(raw_df):
    cleaned, report = clean_dataframe(raw_df)
    assert report.cancelled_rows_kept == 1
    assert "NS-2026-00003" in cleaned["Order ID"].values
    # Cancelled rows are present but excluded from revenue.
    assert "NS-2026-00003" not in revenue_eligible(cleaned)["Order ID"].values


def test_calculated_fields(raw_df):
    cleaned, _ = clean_dataframe(raw_df)
    row = cleaned.loc[cleaned["Order ID"] == "NS-2026-00001"].iloc[0]
    assert row["Gross Revenue"] == pytest.approx(1 * 1299.0)
    assert row["Discount Amount"] == pytest.approx(1299.0 * 0.1)
    assert row["Net Revenue"] == pytest.approx(1299.0 * 0.9)


def test_dates_normalized(raw_df):
    cleaned, report = clean_dataframe(raw_df)
    assert report.dates_normalized >= 1
    assert pd.api.types.is_datetime64_any_dtype(cleaned["Order Date"])
