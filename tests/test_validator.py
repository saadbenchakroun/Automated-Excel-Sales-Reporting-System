"""Tests for dataset validation."""

from __future__ import annotations

import pandas as pd

from src.data_validator import validate_dataframe
from tests.conftest import clean_rows

STATUSES = ["Completed", "Pending", "Processing", "Cancelled", "Refunded"]


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_valid_data_passes():
    result = validate_dataframe(_frame(clean_rows()), allowed_statuses=STATUSES)
    assert result.valid is True
    assert result.error_count == 0
    assert result.rows_rejected == 0
    assert result.rows_checked == 3


def test_missing_required_column_fails():
    frame = _frame(clean_rows()).drop(columns=["Quantity"])
    result = validate_dataframe(frame, allowed_statuses=STATUSES)
    assert result.valid is False
    assert any("Quantity" in e.message for e in result.errors)
    assert result.rows_rejected == len(frame)


def test_invalid_quantity_is_error():
    rows = clean_rows()
    rows[1]["Quantity"] = -5
    result = validate_dataframe(_frame(rows), allowed_statuses=STATUSES)
    assert result.valid is False
    assert any(e.field == "Quantity" and e.severity == "error" for e in result.errors)


def test_non_numeric_price_is_error():
    rows = clean_rows()
    rows[0]["Unit Price"] = "expensive"
    result = validate_dataframe(_frame(rows), allowed_statuses=STATUSES)
    assert result.valid is False
    assert any(e.field == "Unit Price" and e.severity == "error" for e in result.errors)


def test_invalid_date_is_error():
    rows = clean_rows()
    rows[0]["Order Date"] = "not-a-date"
    result = validate_dataframe(_frame(rows), allowed_statuses=STATUSES)
    assert result.valid is False
    assert any(e.field == "Order Date" and e.severity == "error" for e in result.errors)


def test_unknown_status_is_error():
    rows = clean_rows()
    rows[0]["Order Status"] = "Shipped"
    result = validate_dataframe(_frame(rows), allowed_statuses=STATUSES)
    assert result.valid is False
    assert any(e.field == "Order Status" and e.severity == "error" for e in result.errors)


def test_missing_discount_is_warning_not_error():
    rows = clean_rows()
    rows[0]["Discount"] = None
    result = validate_dataframe(_frame(rows), allowed_statuses=STATUSES)
    assert result.valid is True
    assert any(e.field == "Discount" and e.severity == "warning" for e in result.warnings)
