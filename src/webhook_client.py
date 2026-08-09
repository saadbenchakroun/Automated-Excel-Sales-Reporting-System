"""Delivery of the generated report to an n8n webhook."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.config import Config
from src.models import WebhookResult

logger = logging.getLogger("sales_reporting.webhook")

REPORT_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_payload(config: Config, report_path: Path, metrics: dict) -> dict:
    """Construct the metadata payload sent alongside the report file."""
    return {
        "status": "success",
        "company_name": config.company_name,
        "currency": config.currency,
        "report_name": report_path.name,
        "report_path": str(report_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_revenue": metrics.get("total_revenue"),
        "total_orders": metrics.get("total_orders"),
        "total_units": metrics.get("total_units"),
        "period_start": metrics.get("period_start"),
        "period_end": metrics.get("period_end"),
    }


def send_report(
    config: Config,
    report_path: Path,
    metrics: dict,
    *,
    session: requests.Session | None = None,
) -> WebhookResult:
    """POST the report file and its metadata to the configured n8n webhook.

    The request is retried with exponential backoff. If the report was generated
    successfully but every attempt fails, the local report is left untouched and
    a failed ``WebhookResult`` is returned (the caller decides what to do next).
    """
    session = session or requests.Session()
    payload = build_payload(config, report_path, metrics)

    files = None
    if config.webhook_include_attachment and report_path.exists():
        files = {
            "report": (
                report_path.name,
                open(report_path, "rb"),
                REPORT_MIME,
            )
        }

    last_error = ""
    status_code: int | None = None
    attempts = 0

    for attempt in range(1, config.webhook_max_attempts + 1):
        attempts = attempt
        try:
            logger.info(
                "Sending webhook to %s (attempt %d/%d)",
                config.webhook_url,
                attempt,
                config.webhook_max_attempts,
            )
            response = session.post(
                config.webhook_url,
                data=payload,
                files=files,
                timeout=config.webhook_timeout,
            )
            status_code = response.status_code
            if response.ok:
                logger.info("Webhook succeeded (status=%s)", status_code)
                return WebhookResult(success=True, attempts=attempts, status_code=status_code, message="ok")

            last_error = f"HTTP {status_code}: {response.text[:300]}"
            logger.warning("Webhook attempt %d failed: %s", attempt, last_error)
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning("Webhook attempt %d raised error: %s", attempt, last_error)
        finally:
            if attempt < config.webhook_max_attempts:
                backoff = config.webhook_backoff_base * (2 ** (attempt - 1))
                logger.info("Retrying webhook in %ds", backoff)
                time.sleep(backoff)

    if files:
        files["report"][1].close()

    logger.error("Webhook delivery failed after %d attempts: %s", attempts, last_error)
    return WebhookResult(success=False, attempts=attempts, status_code=status_code, message=last_error)
