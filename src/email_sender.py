"""Direct SMTP email delivery for the generated report.

Works alongside the n8n webhook — both can be enabled at the same time.
Uses stdlib smtplib + email.message so no extra dependency is needed.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from src.config import Config
from src.models import EmailResult

logger = logging.getLogger("sales_reporting.email")

REPORT_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_email_message(
    config: Config,
    report_path: Path,
    metrics: dict,
) -> EmailMessage:
    """Build an EmailMessage with the report attached."""
    today = date.today().isoformat()
    subject = config.email_subject_template.format(
        company=config.company_name,
        date=today,
        report_name=report_path.name,
    )

    # Human-readable body — mirrors the webhook payload but as text.
    period = f"{metrics.get('period_start', 'N/A')} to {metrics.get('period_end', 'N/A')}"
    body_lines = [
        f"Hello,",
        "",
        f"Please find attached the sales report for {config.company_name}.",
        "",
        f"Report: {report_path.name}",
        f"Period: {period}",
        f"Generated: {today}",
        "",
        f"Total revenue: {config.currency_symbol}{metrics.get('total_revenue', 'N/A')}",
        f"Total orders: {metrics.get('total_orders', 'N/A')}",
        f"Total units: {metrics.get('total_units', 'N/A')}",
        "",
        "This email was sent automatically by the Sales Reporting System.",
        "Reply to this address if you have questions.",
    ]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.email_from
    msg["To"] = config.email_to
    msg.set_content("\n".join(body_lines))

    # Attach the workbook
    if report_path.exists():
        data = report_path.read_bytes()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=report_path.name,
        )
    else:
        logger.warning("Report file not found for attachment: %s", report_path)

    return msg


def send_email(
    config: Config,
    report_path: Path,
    metrics: dict,
) -> EmailResult:
    """Send the report via SMTP. Returns EmailResult (never raises)."""
    if not config.email_enabled:
        return EmailResult(success=False, message="Email disabled in config")

    if not config.email_smtp_host or not config.email_from or not config.email_to:
        msg = "Email is enabled but SMTP_HOST / EMAIL_FROM / EMAIL_TO is missing"
        logger.error(msg)
        return EmailResult(success=False, message=msg)

    msg = build_email_message(config, report_path, metrics)

    try:
        logger.info(
            "Sending email via %s:%s to %s (TLS=%s)",
            config.email_smtp_host,
            config.email_smtp_port,
            config.email_to,
            config.email_use_tls,
        )

        if config.email_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(
                config.email_smtp_host,
                config.email_smtp_port,
                timeout=config.email_timeout,
            ) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                if config.email_smtp_user and config.email_smtp_pass:
                    server.login(config.email_smtp_user, config.email_smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(
                config.email_smtp_host,
                config.email_smtp_port,
                timeout=config.email_timeout,
            ) as server:
                if config.email_smtp_user and config.email_smtp_pass:
                    server.login(config.email_smtp_user, config.email_smtp_pass)
                server.send_message(msg)

        logger.info("Email sent successfully to %s", config.email_to)
        return EmailResult(success=True, message="ok", recipient=config.email_to)

    except Exception as exc:  # noqa: BLE001
        logger.error("Email delivery failed: %s", exc)
        return EmailResult(success=False, message=str(exc), recipient=config.email_to)
