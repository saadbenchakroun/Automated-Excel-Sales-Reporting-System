"""Send-only test: deliver the latest report to the configured n8n webhook.

Runs just the webhook delivery step (no data load / clean / report build).
Usage:  .venv/Scripts/python.exe scripts/send_webhook_only.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.webhook_client import send_report

config = Config.load(require_webhook=True)

reports = sorted(Path("reports").glob("sales_report_*.xlsx"))
if not reports:
    raise SystemExit("No report found in reports/ — run the pipeline first.")
report_path = reports[-1]
print(f"Sending: {report_path.name}")

metrics = {
    "total_revenue": 416158.16,
    "total_orders": 1161,
    "total_units": 1825,
    "period_start": "2026-01-01",
    "period_end": "2026-06-30",
}

result = send_report(config, report_path, metrics)
print(f"RESULT: success={result.success} status_code={result.status_code} "
      f"attempts={result.attempts} message={result.message}")
