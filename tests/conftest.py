"""Shared fixtures for the test suite."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.config import Config


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """A Config instance wired to a temporary project layout."""
    return Config(
        company_name="Northstar Commerce",
        currency="USD",
        currency_symbol="$",
        input_folder=tmp_path / "data" / "input",
        output_folder=tmp_path / "reports",
        processed_folder=tmp_path / "data" / "processed",
        log_folder=tmp_path / "logs",
        report_filename_pattern="sales_report_{date}.xlsx",
        include_raw_data=True,
        log_level="INFO",
        log_file="automation.log",
        log_max_bytes=1024 * 1024,
        log_backup_count=1,
        allowed_order_statuses=["Completed", "Pending", "Processing", "Cancelled", "Refunded"],
        max_discount=1.0,
        webhook_enabled=False,
        webhook_url="http://localhost:5678/webhook/test",
        webhook_timeout=5,
        webhook_max_attempts=3,
        webhook_backoff_base=0,
        webhook_include_attachment=True,
    )


def clean_rows() -> list[dict]:
    """A small fully-clean dataset (no data-quality problems)."""
    return [
        {
            "Order ID": "NS-2026-00001",
            "Order Date": datetime(2026, 1, 5),
            "Customer ID": "C-1001",
            "Customer Name": "Amelia Hart",
            "Product ID": "P-001",
            "Product Name": "Laptop Pro 14",
            "Category": "Electronics",
            "Quantity": 1,
            "Unit Price": 1299.00,
            "Discount": 0.1,
            "Salesperson": "Alex Morgan",
            "Region": "North America",
            "Payment Method": "Credit Card",
            "Order Status": "Completed",
        },
        {
            "Order ID": "NS-2026-00002",
            "Order Date": datetime(2026, 1, 8),
            "Customer ID": "C-1002",
            "Customer Name": "Liam O'Connor",
            "Product ID": "P-011",
            "Product Name": "Ergonomic Office Chair",
            "Category": "Office Equipment",
            "Quantity": 2,
            "Unit Price": 349.99,
            "Discount": 0.0,
            "Salesperson": "Priya Sharma",
            "Region": "Europe",
            "Payment Method": "PayPal",
            "Order Status": "Completed",
        },
        {
            "Order ID": "NS-2026-00003",
            "Order Date": datetime(2026, 1, 12),
            "Customer ID": "C-1003",
            "Customer Name": "Noah Patel",
            "Product ID": "P-002",
            "Product Name": "Wireless Mouse",
            "Category": "Electronics",
            "Quantity": 5,
            "Unit Price": 34.99,
            "Discount": 0.2,
            "Salesperson": "Alex Morgan",
            "Region": "North America",
            "Payment Method": "Credit Card",
            "Order Status": "Cancelled",
        },
    ]


@pytest.fixture
def clean_df() -> pd.DataFrame:
    """A cleaned-shaped DataFrame (with calculated fields)."""
    df = pd.DataFrame(clean_rows())
    df["Source File"] = "sales_2026_01.xlsx"
    df["Gross Revenue"] = df["Quantity"] * df["Unit Price"]
    df["Discount Amount"] = df["Gross Revenue"] * df["Discount"]
    df["Net Revenue"] = df["Gross Revenue"] - df["Discount Amount"]
    return df


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """A raw DataFrame (before cleaning) containing a few common problems."""
    rows = clean_rows()
    rows.append(dict(rows[0]))  # exact duplicate
    rows.append({
        "Order ID": "NS-2026-00004",
        "Order Date": "2026.02.01",
        "Customer ID": "C-1004",
        "Customer Name": "  ",
        "Product ID": "P-003",
        "Product Name": '27" LED Monitor',
        "Category": "electronics ",
        "Quantity": 1,
        "Unit Price": 219.99,
        "Discount": None,
        "Salesperson": "  daniel kim ",
        "Region": "north america",
        "Payment Method": "Bank Transfer",
        "Order Status": "Completed",
    })
    rows.append({
        "Order ID": "NS-2026-00005",
        "Order Date": datetime(2026, 2, 3),
        "Customer ID": "C-1005",
        "Customer Name": "Ethan Nguyen",
        "Product ID": "P-002",
        "Product Name": "Wireless Mouse",
        "Category": "Electronics",
        "Quantity": -3,
        "Unit Price": 34.99,
        "Discount": 0.0,
        "Salesperson": "Alex Morgan",
        "Region": "North America",
        "Payment Method": "Credit Card",
        "Order Status": "Completed",
    })
    return pd.DataFrame(rows)
