"""Data structures used across the reporting pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FileInfo:
    """Metadata about one discovered input file."""

    path: Path
    rows_loaded: int
    sheet_used: str
    status: str = "ok"
    message: str = ""


@dataclass
class ValidationIssue:
    """A single problem found while validating a dataset."""

    row_index: int | None
    field: str
    severity: str  # "warning" or "error"
    message: str


@dataclass
class ValidationResult:
    """Aggregated outcome of dataset validation."""

    valid: bool
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)
    rows_checked: int = 0
    rows_rejected: int = 0

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def error_count(self) -> int:
        return len(self.errors)


@dataclass
class CleaningReport:
    """Counts describing what the cleaning pipeline changed."""

    rows_before: int = 0
    rows_after_duplicates: int = 0
    duplicate_rows_removed: int = 0
    invalid_rows_removed: int = 0
    missing_customer_names_filled: int = 0
    missing_discounts_filled: int = 0
    whitespace_trimmed_cells: int = 0
    dates_normalized: int = 0
    cancelled_rows_kept: int = 0
    rows_final: int = 0

    @property
    def rows_excluded(self) -> int:
        return self.rows_before - self.rows_final


@dataclass
class AnalyticsResult:
    """Metrics and breakdowns produced by the analytics module."""

    metrics: dict[str, Any]
    monthly: Any
    by_category: Any
    by_product: Any
    by_salesperson: Any
    by_region: Any
    by_payment_method: Any
    top_customers: Any
    top_products: Any
    top_salespeople: Any


@dataclass
class WebhookResult:
    """Outcome of the n8n webhook delivery."""

    success: bool
    attempts: int = 0
    status_code: int | None = None
    message: str = ""


@dataclass
class PipelineResult:
    """Everything produced by a full pipeline run."""

    files_processed: list[FileInfo]
    validation: ValidationResult
    cleaning: CleaningReport
    analytics: AnalyticsResult
    report_path: Path | None
    webhook: WebhookResult | None
    started_at: datetime
    finished_at: datetime
