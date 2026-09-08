"""Pipeline orchestrator: wires discovery, loading, validation, cleaning,
analytics, report generation and webhook delivery together."""

from __future__ import annotations

import logging
from datetime import datetime

from src import data_cleaner, data_loader, data_validator
from src.analytics import compute_all
from src.config import Config
from src.email_sender import send_email
from src.models import PipelineResult
from src.report_generator import generate_report
from src.webhook_client import send_report

logger = logging.getLogger("sales_reporting.pipeline")


def run_pipeline(config: Config) -> PipelineResult:
    """Execute the full reporting pipeline and return its results."""
    started_at = datetime.now()
    logger.info("=== Pipeline start ===")
    logger.info("Company: %s | Currency: %s", config.company_name, config.currency)

    # 1. Discover input files.
    files = data_loader.discover_files(config.input_folder)
    logger.info("Discovered %d Excel file(s) in %s", len(files), config.input_folder)
    for path in files:
        logger.info("  - %s", path.name)

    # 2. Load and combine.
    combined, file_infos = data_loader.load_files(files)
    logger.info("Loaded %d rows across %d file(s)", len(combined), len(file_infos))
    for info in file_infos:
        if info.status == "ok":
            logger.info("  - %s: %d rows (sheet=%s)", info.path.name, info.rows_loaded, info.sheet_used)
        else:
            logger.warning("  - %s: FAILED (%s)", info.path.name, info.message)

    # 3. Validate.
    validation = data_validator.validate_dataframe(
        combined,
        allowed_statuses=config.allowed_order_statuses,
        max_discount=config.max_discount,
    )
    logger.info(
        "Validation: %s | rows=%d errors=%d warnings=%d rejected=%d",
        "valid" if validation.valid else "invalid",
        validation.rows_checked,
        validation.error_count,
        validation.warning_count,
        validation.rows_rejected,
    )

    # 4. Clean.
    cleaned, cleaning_report = data_cleaner.clean_dataframe(combined)
    logger.info(
        "Cleaning: rows %d -> %d (duplicates removed=%d, invalid removed=%d)",
        cleaning_report.rows_before,
        cleaning_report.rows_final,
        cleaning_report.duplicate_rows_removed,
        cleaning_report.invalid_rows_removed,
    )

    # 5. Analytics.
    analytics_result = compute_all(cleaned)
    metrics = analytics_result.metrics
    logger.info(
        "Analytics: total_revenue=%s orders=%d units=%d customers=%d cancellation_rate=%s%%",
        metrics["total_revenue"],
        metrics["total_orders"],
        metrics["total_units"],
        metrics["total_customers"],
        metrics["cancellation_rate"],
    )

    # 6. Generate the Excel report.
    report_path = generate_report(
        config,
        cleaned,
        file_infos,
        validation,
        cleaning_report,
        analytics_result,
    )

    # 7. Deliver to n8n (if enabled).
    webhook_result = None
    if config.webhook_enabled:
        webhook_result = send_report(config, report_path, metrics)
        if webhook_result.success:
            logger.info("Webhook delivery succeeded (status=%s)", webhook_result.status_code)
        else:
            logger.error(
                "Webhook delivery FAILED after %d attempt(s): %s",
                webhook_result.attempts,
                webhook_result.message,
            )
            logger.error("Report remains available locally at %s", report_path)
    else:
        logger.info("Webhook disabled - report saved locally only.")

    # 8. Deliver via direct SMTP email (if enabled, independent of webhook).
    email_result = None
    if config.email_enabled:
        email_result = send_email(config, report_path, metrics)
        if email_result.success:
            logger.info("Email delivery succeeded to %s", email_result.recipient)
        else:
            logger.error("Email delivery FAILED: %s", email_result.message)
            logger.error("Report remains available locally at %s", report_path)
    else:
        logger.info("Direct email disabled.")

    finished_at = datetime.now()
    logger.info("=== Pipeline finished in %s ===", finished_at - started_at)

    return PipelineResult(
        files_processed=file_infos,
        validation=validation,
        cleaning=cleaning_report,
        analytics=analytics_result,
        report_path=report_path,
        webhook=webhook_result,
        email=email_result,
        started_at=started_at,
        finished_at=finished_at,
    )
