"""Generate realistic monthly sales Excel files for Northstar Commerce.

Creates six monthly workbooks (sales_2026_01.xlsx ... sales_2026_06.xlsx)
inside ``data/input``. The data is deterministic for a given seed and contains
a small, realistic amount of data-quality problems on purpose (duplicates,
missing names, inconsistent capitalization, bad numbers, etc.) so the cleaning
and validation pipeline can be demonstrated.

Run from the project root::

    python -m scripts.generate_sample_data --seed 42
"""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FOLDER = PROJECT_ROOT / "data" / "input"

COLUMNS = [
    "Order ID",
    "Order Date",
    "Customer ID",
    "Customer Name",
    "Product ID",
    "Product Name",
    "Category",
    "Quantity",
    "Unit Price",
    "Discount",
    "Salesperson",
    "Region",
    "Payment Method",
    "Order Status",
]

PRODUCTS = [
    ("P-001", "Laptop Pro 14", "Electronics", 1299.00),
    ("P-002", "Wireless Mouse", "Electronics", 34.99),
    ("P-003", '27" LED Monitor', "Electronics", 219.99),
    ("P-004", "Mechanical Keyboard", "Electronics", 89.99),
    ("P-005", "USB-C Hub", "Electronics", 49.99),
    ("P-006", "Bluetooth Speaker", "Electronics", 79.99),
    ("P-007", "HD Webcam", "Electronics", 64.99),
    ("P-008", "Noise-Cancelling Headphones", "Electronics", 199.99),
    ("P-009", "Portable SSD 1TB", "Electronics", 149.99),
    ("P-010", "Wireless Charger", "Electronics", 29.99),
    ("P-011", "Ergonomic Office Chair", "Office Equipment", 349.99),
    ("P-012", "Standing Desk", "Office Equipment", 599.99),
    ("P-013", "Document Shredder", "Office Equipment", 119.99),
    ("P-014", "Laser Printer", "Office Equipment", 279.99),
    ("P-015", "LED Desk Lamp", "Office Equipment", 44.99),
    ("P-016", "Filing Cabinet", "Office Equipment", 159.99),
    ("P-017", "Whiteboard 60x40", "Office Equipment", 89.99),
    ("P-018", "Paper Ream (500 sheets)", "Office Equipment", 6.99),
    ("P-019", "Desktop Computer", "Electronics", 999.99),
    ("P-020", "Video Conferencing Kit", "Electronics", 499.99),
]

CUSTOMERS = [
    ("C-1001", "Amelia Hart"), ("C-1002", "Liam O'Connor"), ("C-1003", "Noah Patel"),
    ("C-1004", "Olivia Bennett"), ("C-1005", "Ethan Nguyen"), ("C-1006", "Sophia Rossi"),
    ("C-1007", "Mason Kim"), ("C-1008", "Isabella Moreau"), ("C-1009", "Lucas Silva"),
    ("C-1010", "Mia Johansson"), ("C-1011", "James Carter"), ("C-1012", "Charlotte Dubois"),
    ("C-1013", "Benjamin Adams"), ("C-1014", "Amelia Fischer"), ("C-1015", "Lucas Alvarez"),
    ("C-1016", "Harper Wilson"), ("C-1017", "Henry Walker"), ("C-1018", "Ella Martin"),
    ("C-1019", "Alexander Clark"), ("C-1020", "Grace Robinson"), ("C-1021", "Daniel Young"),
    ("C-1022", "Chloe Hernandez"), ("C-1023", "Michael Lewis"), ("C-1024", "Ava Scott"),
    ("C-1025", "Matthew King"), ("C-1026", "Emily Moore"), ("C-1027", "Jack Taylor"),
    ("C-1028", "Lily White"), ("C-1029", "Ryan Harris"), ("C-1030", "Zoe Thompson"),
    ("C-1031", "David Anderson"), ("C-1032", "Maya Lee"), ("C-1033", "Chris Johnson"),
    ("C-1034", "Nora Allen"), ("C-1035", "Sam Green"), ("C-1036", "Eva Brown"),
    ("C-1037", "Oscar Nelson"), ("C-1038", "Ruby Hall"), ("C-1039", "Leo Wright"),
    ("C-1040", "Ivy Hill"),
]

SALESPEOPLE = ["Alex Morgan", "Priya Sharma", "Jordan Lee", "Sofia Ramirez", "Daniel Kim", "Emma Wilson"]
REGIONS = ["North America", "Europe", "Asia Pacific", "South America"]
PAYMENT_METHODS = ["Credit Card", "PayPal", "Bank Transfer", "Apple Pay", "Debit Card"]
STATUS_WEIGHTS = (
    ["Completed"] * 20
    + ["Pending"] * 2
    + ["Processing"] * 2
    + ["Cancelled", "Refunded"]
)

# Small lookup helpers keyed by product code.
PRODUCT_BY_ID = {p[0]: p for p in PRODUCTS}
CUSTOMER_BY_ID = {c[0]: c for c in CUSTOMERS}


def _next_order_id(counter: list[int]) -> str:
    counter[0] += 1
    return f"NS-2026-{counter[0]:05d}"


def _make_row(rng: random.Random, counter: list[int], month_start: date, month_end: date) -> dict:
    product_id, product_name, category, unit_price = rng.choice(PRODUCTS)
    customer_id, customer_name = rng.choice(CUSTOMERS)
    salesperson = rng.choice(SALESPEOPLE)
    region = rng.choice(REGIONS)
    payment = rng.choice(PAYMENT_METHODS)
    status = rng.choice(STATUS_WEIGHTS)
    quantity = rng.choices([1, 1, 1, 2, 2, 3, 4, 5], weights=[30, 20, 15, 15, 8, 7, 3, 2])[0]
    discount = round(rng.choice([0.0, 0.0, 0.05, 0.1, 0.15, 0.2]), 2)
    order_date = month_start + timedelta(days=rng.randint(0, (month_end - month_start).days))
    return {
        "Order ID": _next_order_id(counter),
        "Order Date": order_date,
        "Customer ID": customer_id,
        "Customer Name": customer_name,
        "Product ID": product_id,
        "Product Name": product_name,
        "Category": category,
        "Quantity": quantity,
        "Unit Price": unit_price,
        "Discount": discount,
        "Salesperson": salesperson,
        "Region": region,
        "Payment Method": payment,
        "Order Status": status,
    }


def _inject_problems(rng: random.Random, rows: list[dict]) -> list[dict]:
    """Add a small, realistic set of data-quality problems."""
    if not rows:
        return rows

    # 1. Exact duplicates (append two full copies).
    for _ in range(2):
        rows.append(dict(rng.choice(rows)))

    # 2. Missing customer names.
    for _ in range(2):
        rng.choice(rows)["Customer Name"] = ""

    # 3. Trailing whitespace.
    for _ in range(3):
        row = rng.choice(rows)
        field = rng.choice(["Customer Name", "Product Name", "Salesperson"])
        row[field] = str(row[field]) + "  "

    # 4. Inconsistent capitalization / category & region variants.
    for _ in range(3):
        row = rng.choice(rows)
        variant = rng.choice(["lower", "upper", "title"])
        if variant == "lower":
            row["Category"] = str(row["Category"]).lower()
        elif variant == "upper":
            row["Region"] = str(row["Region"]).upper()
        else:
            row["Category"] = str(row["Category"]) + " "
    for _ in range(2):
        row = rng.choice(rows)
        row["Region"] = rng.choice(["north america", "APAC", "europe", "South america"])

    # 5. Missing discounts.
    for _ in range(3):
        rng.choice(rows)["Discount"] = None

    # 6. Inconsistent date representations.
    for _ in range(2):
        row = rng.choice(rows)
        d: date = row["Order Date"]
        if rng.random() < 0.5:
            row["Order Date"] = d.strftime("%d/%m/%Y")
        else:
            row["Order Date"] = d.strftime("%Y.%m.%d")

    # 7. Invalid quantities.
    qty_problems = [-1, "N/A"]
    for problem in qty_problems:
        rng.choice(rows)["Quantity"] = problem

    # 8. Invalid price (negative).
    rng.choice(rows)["Unit Price"] = -20.0

    return rows


def generate(seed: int = 42, output_folder: Path | None = None) -> int:
    """Generate the six monthly files. Returns 0 on success."""
    output_folder = output_folder or INPUT_FOLDER
    output_folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    counter = [0]

    year = 2026
    month_names = [
        ("01", 31), ("02", 28), ("03", 31), ("04", 30),
        ("05", 31), ("06", 30),
    ]

    generated = 0
    for month_num, days_in_month in month_names:
        month_start = date(year, int(month_num), 1)
        month_end = date(year, int(month_num), days_in_month)
        row_count = rng.randint(100, 300)
        rows = [_make_row(rng, counter, month_start, month_end) for _ in range(row_count)]
        rows = _inject_problems(rng, rows)

        frame = pd.DataFrame(rows, columns=COLUMNS)
        filename = f"sales_{year}_{month_num}.xlsx"
        path = output_folder / filename
        frame.to_excel(path, sheet_name="Sales", index=False, engine="openpyxl")
        generated += 1
        print(f"Wrote {path} ({len(frame)} rows)")

    print(f"\nGenerated {generated} sample files in {output_folder}")
    print("Each file intentionally contains a small number of data-quality problems "
          "to exercise the validation and cleaning pipeline.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--output", type=Path, default=None, help="Output folder (default: data/input)")
    args = parser.parse_args()
    return generate(seed=args.seed, output_folder=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
