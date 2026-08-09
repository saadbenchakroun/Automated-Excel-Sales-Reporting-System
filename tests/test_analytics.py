"""Tests for analytics metrics and breakdowns."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.analytics import compute_all, compute_metrics, compute_monthly


def test_total_revenue_excludes_cancelled(clean_df):
    metrics = compute_metrics(clean_df)
    # Rows 1 + 2 are completed; row 3 is cancelled.
    assert metrics["total_revenue"] == round(1169.10 + 699.98, 2)
    assert metrics["gross_revenue"] == round(1299.0 + 699.98, 2)
    assert metrics["total_discounts"] == round(129.90, 2)


def test_orders_and_units(clean_df):
    metrics = compute_metrics(clean_df)
    assert metrics["total_orders"] == 2
    assert metrics["total_units"] == 3


def test_average_order_value(clean_df):
    metrics = compute_metrics(clean_df)
    assert metrics["avg_order_value"] == round(metrics["total_revenue"] / 2, 2)
    assert metrics["avg_units_per_order"] == 1.5


def test_cancellation_rate(clean_df):
    metrics = compute_metrics(clean_df)
    assert metrics["cancelled_orders"] == 1
    assert metrics["all_orders"] == 3
    assert metrics["cancellation_rate"] == round(1 / 3 * 100, 2)


def test_mom_growth_division_by_zero():
    df = pd.DataFrame([{
        "Order ID": "O1",
        "Order Date": datetime(2026, 1, 10),
        "Customer ID": "C1",
        "Customer Name": "A",
        "Product ID": "P1",
        "Product Name": "P",
        "Category": "C",
        "Quantity": 1,
        "Unit Price": 10.0,
        "Discount": 0.0,
        "Salesperson": "S",
        "Region": "R",
        "Payment Method": "PM",
        "Order Status": "Completed",
        "Gross Revenue": 10.0,
        "Discount Amount": 0.0,
        "Net Revenue": 10.0,
    }])
    monthly = compute_monthly(df)
    assert monthly.iloc[0]["mom_growth_pct"] == 0.0


def test_mom_growth_calculation():
    def row(oid, day, price):
        return {
            "Order ID": oid, "Order Date": datetime(2026, 1, day),
            "Customer ID": "C1", "Customer Name": "A", "Product ID": "P1",
            "Product Name": "P", "Category": "C", "Quantity": 1,
            "Unit Price": price, "Discount": 0.0, "Salesperson": "S",
            "Region": "R", "Payment Method": "PM", "Order Status": "Completed",
            "Gross Revenue": price, "Discount Amount": 0.0, "Net Revenue": price,
        }

    df = pd.DataFrame([
        row("O1", 5, 100.0),
        row("O2", 6, 50.0),   # January total 150
        row("O3", 5, 300.0),  # February total 300
    ])
    df.loc[df["Order ID"] == "O3", "Order Date"] = datetime(2026, 2, 5)
    monthly = compute_monthly(df)
    assert monthly.iloc[0]["net_revenue"] == 150.0
    assert monthly.iloc[1]["net_revenue"] == 300.0
    assert monthly.iloc[1]["mom_growth_pct"] == round((300 - 150) / 150 * 100, 2)


def test_breakdown_by_category(clean_df):
    result = compute_all(clean_df)
    cat = result.by_category
    assert cat.iloc[0]["Category"] == "Electronics"
    assert cat.iloc[0]["net_revenue"] == round(1169.10, 2)
    assert cat.iloc[1]["Category"] == "Office Equipment"
    assert cat.iloc[1]["net_revenue"] == round(699.98, 2)


def test_top_customers_and_products(clean_df):
    result = compute_all(clean_df)
    assert len(result.top_customers) == 2
    assert len(result.top_products) == 2
    assert result.metrics["top_category"] == "Electronics"
