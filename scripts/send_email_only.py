"""Send-only test: deliver the latest report via direct SMTP email.

Runs just the email delivery step (no data load / clean / report build).
Requires email.enabled=true and SMTP_* / EMAIL_* vars in .env.
Usage:  .venv/Scripts/python.exe scripts/send_email_only.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.email_sender import send_email

config = Config.load(require_webhook=False)

if not config.email_enabled:
    print("Email is disabled in config.yaml (email.enabled=false).")
    print("Enable it and set SMTP_HOST, EMAIL_FROM, EMAIL_TO in .env, then retry.")
    raise SystemExit(1)

reports = sorted(Path("reports").glob("sales_report_*.xlsx"))
if not reports:
    raise SystemExit("No report found in reports/ — run the pipeline first.")
report_path = reports[-1]
print(f"Sending: {report_path.name} to {config.email_to} via {config.email_smtp_host}:{config.email_smtp_port}")

metrics = {
    "total_revenue": 416158.16,
    "total_orders": 1161,
    "total_units": 1825,
    "period_start": "2026-01-01",
    "period_end": "2026-06-30",
}

result = send_email(config, report_path, metrics)
print(f"RESULT: success={result.success} recipient={result.recipient} message={result.message}")
