"""Configuration loading and environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.exceptions import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@dataclass
class Config:
    """Runtime configuration for the reporting pipeline."""

    company_name: str
    currency: str
    currency_symbol: str

    input_folder: Path
    output_folder: Path
    processed_folder: Path
    log_folder: Path

    report_filename_pattern: str
    include_raw_data: bool

    log_level: str
    log_file: str
    log_max_bytes: int
    log_backup_count: int

    allowed_order_statuses: list[str]
    max_discount: float

    webhook_enabled: bool
    webhook_url: str
    webhook_timeout: int
    webhook_max_attempts: int
    webhook_backoff_base: int
    webhook_include_attachment: bool

    env_file: str = field(default=".env")

    @classmethod
    def load(
        cls,
        config_path: str | Path | None = None,
        env_file: str = ".env",
        require_webhook: bool = True,
    ) -> "Config":
        """Load configuration from a YAML file and environment overrides.

        Values that contain a ``${VAR}`` placeholder are resolved from the
        environment.

        ``require_webhook`` lets callers that intend to disable the webhook
        (for example ``run.py --no-webhook``) skip the missing-URL error.
        """
        config_path = Path(config_path) if config_path else PROJECT_ROOT / "config.yaml"
        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        with open(config_path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

        load_dotenv(PROJECT_ROOT / env_file)

        app = raw.get("app", {})
        paths = raw.get("paths", {})
        report = raw.get("report", {})
        logging_cfg = raw.get("logging", {})
        validation = raw.get("validation", {})
        webhook = raw.get("webhook", {})

        def resolve(value: str) -> str:
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                return os.getenv(env_name, "")
            return value

        webhook_url = resolve(str(webhook.get("url", "")))
        # If the env var is set, make sure the webhook is enabled even if config says no.
        webhook_enabled = bool(
            webhook.get("enabled", True) or (webhook_url and webhook_url != "")
        )

        config = cls(
            company_name=str(app.get("company_name", "Northstar Commerce")),
            currency=str(app.get("currency", "USD")),
            currency_symbol=str(app.get("currency_symbol", "$")),
            input_folder=_resolve_path(str(paths.get("input_folder", "data/input"))),
            output_folder=_resolve_path(str(paths.get("output_folder", "reports"))),
            processed_folder=_resolve_path(str(paths.get("processed_folder", "data/processed"))),
            log_folder=_resolve_path(str(paths.get("log_folder", "logs"))),
            report_filename_pattern=str(report.get("filename_pattern", "sales_report_{date}.xlsx")),
            include_raw_data=bool(report.get("include_raw_data", True)),
            log_level=str(logging_cfg.get("level", "INFO")),
            log_file=str(logging_cfg.get("log_file", "automation.log")),
            log_max_bytes=int(logging_cfg.get("max_bytes", 5 * 1024 * 1024)),
            log_backup_count=int(logging_cfg.get("backup_count", 3)),
            allowed_order_statuses=[
                str(s) for s in validation.get("allowed_order_statuses", [])
            ],
            max_discount=float(validation.get("max_discount", 1.0)),
            webhook_enabled=bool(webhook_enabled),
            webhook_url=webhook_url,
            webhook_timeout=int(webhook.get("timeout_seconds", 30)),
            webhook_max_attempts=int(webhook.get("max_attempts", 3)),
            webhook_backoff_base=int(webhook.get("backoff_base_seconds", 2)),
            webhook_include_attachment=bool(webhook.get("include_attachment", True)),
        )
        config.validate(require_webhook=require_webhook)
        return config

    def validate(self, require_webhook: bool = True) -> None:
        """Sanity-check configuration values, raising ConfigError on problems."""
        if not self.company_name:
            raise ConfigError("company_name must not be empty")
        if not self.report_filename_pattern:
            raise ConfigError("report_filename_pattern must not be empty")
        if require_webhook and self.webhook_enabled and not self.webhook_url:
            raise ConfigError(
                "Webhook is enabled but no N8N_WEBHOOK_URL was provided. "
                "Either set the N8N_WEBHOOK_URL environment variable in .env "
                "or run with --no-webhook."
            )
