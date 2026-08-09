"""Validation of raw loaded sales data."""

from __future__ import annotations

import pandas as pd

from src.constants import REQUIRED_COLUMNS, VALID_ORDER_STATUSES
from src.dates import is_datetime_like, parse_datetime
from src.models import ValidationIssue, ValidationResult

DATE_FORMATS_TO_TRY = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%Y.%m.%d",
    "%d.%m.%Y",
    "%b %d, %Y",
    "%d %b %Y",
]


def _parse_date(value: object) -> bool:
    """Return True if *value* can be interpreted as a date."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if is_datetime_like(value):
        return True
    return parse_datetime(value) is not None


def _to_number(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def validate_dataframe(
    frame: pd.DataFrame,
    allowed_statuses: list[str] | None = None,
    max_discount: float = 1.0,
) -> ValidationResult:
    """Validate a raw DataFrame and return a ``ValidationResult``.

    Warnings describe data that can be safely repaired later (for example
    missing discounts or empty customer names). Errors describe records that
    cannot be trusted and will be excluded from the final report.
    """
    if allowed_statuses is None:
        allowed_statuses = sorted(VALID_ORDER_STATUSES)

    warnings: list[ValidationIssue] = []
    errors: list[ValidationIssue] = []

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing_columns:
        issue = ValidationIssue(
            row_index=None,
            field="columns",
            severity="error",
            message=f"Missing required columns: {', '.join(missing_columns)}",
        )
        errors.append(issue)
        # Cannot continue meaningfully, but return partial result for reporting.
        return ValidationResult(
            valid=False,
            warnings=warnings,
            errors=errors,
            rows_checked=len(frame),
            rows_rejected=len(frame),
        )

    rows_checked = len(frame)

    order_ids = frame["Order ID"].astype(object)
    order_dates = frame["Order Date"].astype(object)
    quantities = frame["Quantity"].astype(object)
    prices = frame["Unit Price"].astype(object)
    discounts = frame["Discount"].astype(object) if "Discount" in frame.columns else pd.Series([None] * len(frame))
    statuses = frame["Order Status"].astype(object)
    customers = frame["Customer Name"].astype(object) if "Customer Name" in frame.columns else pd.Series([None] * len(frame))
    categories = frame["Category"].astype(object)
    regions = frame["Region"].astype(object)

    for idx in range(rows_checked):
        row_index = int(frame.index[idx])

        # Order ID
        order_id = str(order_ids.iloc[idx]).strip()
        if not order_id or order_id in {"nan", "None"}:
            errors.append(ValidationIssue(row_index, "Order ID", "error", "Order ID is empty"))

        # Order Date
        if not _parse_date(order_dates.iloc[idx]):
            errors.append(ValidationIssue(row_index, "Order Date", "error", f"Cannot parse date: {order_dates.iloc[idx]!r}"))

        # Quantity
        qty = _to_number(quantities.iloc[idx])
        if qty is None:
            errors.append(ValidationIssue(row_index, "Quantity", "error", f"Quantity is not numeric: {quantities.iloc[idx]!r}"))
        elif qty <= 0:
            errors.append(ValidationIssue(row_index, "Quantity", "error", f"Quantity must be positive, got {qty}"))

        # Unit Price
        price = _to_number(prices.iloc[idx])
        if price is None:
            errors.append(ValidationIssue(row_index, "Unit Price", "error", f"Unit Price is not numeric: {prices.iloc[idx]!r}"))
        elif price < 0:
            errors.append(ValidationIssue(row_index, "Unit Price", "error", f"Unit Price cannot be negative, got {price}"))

        # Discount
        discount = _to_number(discounts.iloc[idx])
        if discount is None:
            warnings.append(ValidationIssue(row_index, "Discount", "warning", "Discount is missing; will be treated as 0"))
        elif discount < 0 or discount > max_discount:
            errors.append(ValidationIssue(row_index, "Discount", "error", f"Discount {discount} outside allowed range [0, {max_discount}]"))

        # Order Status
        status = str(statuses.iloc[idx]).strip()
        if not status or status not in allowed_statuses:
            errors.append(ValidationIssue(row_index, "Order Status", "error", f"Unknown order status: {status!r}"))

        # Optional soft fields
        customer = customers.iloc[idx]
        if customer is None or (isinstance(customer, float) and pd.isna(customer)) or not str(customer).strip():
            warnings.append(ValidationIssue(row_index, "Customer Name", "warning", "Customer name is missing; will be filled"))

        for col, series, label in (("Category", categories, "Category"), ("Region", regions, "Region")):
            value = series.iloc[idx]
            if value is None or (isinstance(value, float) and pd.isna(value)) or not str(value).strip():
                warnings.append(ValidationIssue(row_index, col, "warning", f"{label} is missing"))

    # rows_rejected counts rows with at least one error.
    rejected_indices = {issue.row_index for issue in errors if issue.row_index is not None}
    rows_rejected = len(rejected_indices)

    return ValidationResult(
        valid=len(errors) == 0,
        warnings=warnings,
        errors=errors,
        rows_checked=rows_checked,
        rows_rejected=rows_rejected,
    )
