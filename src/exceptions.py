"""Domain-specific exceptions for the reporting pipeline."""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for all pipeline errors."""


class ConfigError(PipelineError):
    """Raised when configuration cannot be loaded or is invalid."""


class DataDiscoveryError(PipelineError):
    """Raised when the input folder cannot be used for discovery."""


class NoDataFoundError(PipelineError):
    """Raised when no Excel files are found in the input folder."""


class DataLoadError(PipelineError):
    """Raised when an individual Excel file cannot be loaded."""


class ReportGenerationError(PipelineError):
    """Raised when the Excel report cannot be generated."""


class WebhookError(PipelineError):
    """Raised when the report webhook fails permanently."""


class EmailError(PipelineError):
    """Raised when direct email delivery fails permanently."""
