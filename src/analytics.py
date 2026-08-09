"""Business metrics and breakdowns computed from cleaned sales data."""

from __future__ import annotations

import pandas as pd

from src.constants import CANCELLED_STATUSES
from src.data_cleaner import revenue_eligible
from src.models import AnalyticsResult


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide *numerator* by *denominator*, returning *default* on divide-by-zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def _round2(value: float) -> float:
    return round(float(value), 2)


def compute_metrics(df: pd.DataFrame) -> dict:
    """Compute headline business metrics from cleaned data.

    Revenue figures only include orders that are not cancelled or refunded.
    """
    eligible = revenue_eligible(df)

    total_orders = int(eligible["Order ID"].nunique())
    total_revenue = float(eligible["Net Revenue"].sum())
    gross_revenue = float(eligible["Gross Revenue"].sum())
    total_discounts = float(eligible["Discount Amount"].sum())
    total_units = int(eligible["Quantity"].sum())

    cancelled_orders = int(
        df.loc[df["Order Status"].isin(CANCELLED_STATUSES), "Order ID"].nunique()
    )
    all_orders = int(df["Order ID"].nunique())

    metrics = {
        "total_revenue": _round2(total_revenue),
        "gross_revenue": _round2(gross_revenue),
        "total_discounts": _round2(total_discounts),
        "total_orders": total_orders,
        "total_units": total_units,
        "avg_order_value": _round2(_safe_divide(total_revenue, total_orders)),
        "avg_units_per_order": round(_safe_divide(total_units, total_orders), 2),
        "total_customers": int(eligible["Customer ID"].nunique()),
        "total_products": int(eligible["Product ID"].nunique()),
        "cancellation_rate": round(_safe_divide(cancelled_orders, all_orders) * 100, 2),
        "cancelled_orders": cancelled_orders,
        "all_orders": all_orders,
        "period_start": df["Order Date"].min().strftime("%Y-%m-%d") if len(df) else None,
        "period_end": df["Order Date"].max().strftime("%Y-%m-%d") if len(df) else None,
        "top_category": None,
        "top_region": None,
        "top_salesperson": None,
        "top_product": None,
    }
    return metrics


def _breakdown(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Aggregate revenue, orders and units per value of *group_col*."""
    grouped = (
        df.groupby(group_col)
        .agg(
            orders=("Order ID", "nunique"),
            units=("Quantity", "sum"),
            gross_revenue=("Gross Revenue", "sum"),
            discounts=("Discount Amount", "sum"),
            net_revenue=("Net Revenue", "sum"),
        )
        .reset_index()
    )
    grouped["revenue_share"] = _safe_divide(grouped["net_revenue"], grouped["net_revenue"].sum())
    grouped = grouped.sort_values("net_revenue", ascending=False).reset_index(drop=True)
    return grouped


def compute_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue table including month-over-month growth."""
    eligible = revenue_eligible(df)
    monthly = (
        eligible.groupby(eligible["Order Date"].dt.to_period("M"))
        .agg(
            orders=("Order ID", "nunique"),
            units=("Quantity", "sum"),
            gross_revenue=("Gross Revenue", "sum"),
            discounts=("Discount Amount", "sum"),
            net_revenue=("Net Revenue", "sum"),
        )
        .reset_index()
    )
    monthly["month_label"] = monthly["Order Date"].astype(str)
    monthly["month_start"] = monthly["Order Date"].dt.start_time
    monthly = monthly.sort_values("month_start").reset_index(drop=True)

    prev = monthly["net_revenue"].shift(1)
    growth = ((monthly["net_revenue"] - prev) / prev.replace(0, pd.NA)) * 100
    monthly["mom_growth_pct"] = growth.round(2)
    monthly["mom_growth_pct"] = monthly["mom_growth_pct"].fillna(0.0)
    return monthly


def compute_all(df: pd.DataFrame) -> AnalyticsResult:
    """Compute every metric and breakdown needed by the report generator."""
    eligible = revenue_eligible(df)

    monthly = compute_monthly(df)

    by_category = _breakdown(eligible, "Category")
    by_product = _breakdown(eligible, "Product Name")
    by_salesperson = _breakdown(eligible, "Salesperson")
    by_region = _breakdown(eligible, "Region")
    by_payment_method = _breakdown(eligible, "Payment Method")

    # Top N tables include product/customer id columns.
    def _top(frame: pd.DataFrame, n: int) -> pd.DataFrame:
        return frame.head(n).reset_index(drop=True)

    by_product_full = (
        eligible.groupby(["Product ID", "Product Name", "Category"])
        .agg(
            orders=("Order ID", "nunique"),
            units=("Quantity", "sum"),
            net_revenue=("Net Revenue", "sum"),
        )
        .reset_index()
        .sort_values("net_revenue", ascending=False)
        .reset_index(drop=True)
    )
    by_product_full["revenue_share"] = _safe_divide(
        by_product_full["net_revenue"], by_product_full["net_revenue"].sum()
    )

    top_customers = (
        eligible.groupby(["Customer ID", "Customer Name"])
        .agg(
            orders=("Order ID", "nunique"),
            units=("Quantity", "sum"),
            net_revenue=("Net Revenue", "sum"),
        )
        .reset_index()
        .sort_values("net_revenue", ascending=False)
        .reset_index(drop=True)
    )
    top_customers["revenue_share"] = _safe_divide(
        top_customers["net_revenue"], top_customers["net_revenue"].sum()
    )

    metrics = compute_metrics(df)
    metrics["top_category"] = str(by_category.iloc[0]["Category"]) if not by_category.empty else None
    metrics["top_region"] = str(by_region.iloc[0]["Region"]) if not by_region.empty else None
    metrics["top_salesperson"] = str(by_salesperson.iloc[0]["Salesperson"]) if not by_salesperson.empty else None
    metrics["top_product"] = str(by_product_full.iloc[0]["Product Name"]) if not by_product_full.empty else None

    return AnalyticsResult(
        metrics=metrics,
        monthly=monthly,
        by_category=by_category,
        by_product=by_product,
        by_salesperson=by_salesperson,
        by_region=by_region,
        by_payment_method=by_payment_method,
        top_customers=_top(top_customers, 10),
        top_products=_top(by_product_full, 10),
        top_salespeople=by_salesperson,
    )
