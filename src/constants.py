"""Shared column definitions and normalization maps."""

from __future__ import annotations

REQUIRED_COLUMNS: list[str] = [
    "Order ID",
    "Order Date",
    "Customer ID",
    "Product ID",
    "Product Name",
    "Category",
    "Quantity",
    "Unit Price",
    "Salesperson",
    "Region",
    "Payment Method",
    "Order Status",
]

OPTIONAL_COLUMNS: list[str] = [
    "Customer Name",
    "Discount",
]

# Canonical names used to clean inconsistent business attributes.
CANONICAL_CATEGORIES: dict[str, str] = {
    "electronics": "Electronics",
    "office equipment": "Office Equipment",
}

CANONICAL_REGIONS: dict[str, str] = {
    "north america": "North America",
    "europe": "Europe",
    "asia pacific": "Asia Pacific",
    "apac": "Asia Pacific",
    "south america": "South America",
    "latin america": "South America",
    "emea": "Europe",
    "northamerica": "North America",
    "north-america": "North America",
}

# Aliases that map a region to its canonical name even after whitespace/case cleaning.
REGION_ALIASES: dict[str, str] = {
    "us": "North America",
    "usa": "North America",
    "canada": "North America",
    "uk": "Europe",
    "germany": "Europe",
    "france": "Europe",
    "india": "Asia Pacific",
    "australia": "Asia Pacific",
    "japan": "Asia Pacific",
    "brazil": "South America",
}

# Standard Order Status values. Anything else is treated as invalid.
VALID_ORDER_STATUSES: set[str] = {
    "Completed",
    "Pending",
    "Processing",
    "Cancelled",
    "Refunded",
}

CANCELLED_STATUSES: set[str] = {"Cancelled", "Refunded"}

# Columns that are pure text and get whitespace-trimmed.
TEXT_COLUMNS: list[str] = [
    "Order ID",
    "Customer ID",
    "Customer Name",
    "Product ID",
    "Product Name",
    "Category",
    "Salesperson",
    "Region",
    "Payment Method",
    "Order Status",
]

# Columns that must parse as numbers.
NUMERIC_COLUMNS: dict[str, str] = {
    "Quantity": "Quantity",
    "Unit Price": "Unit Price",
    "Discount": "Discount",
}
