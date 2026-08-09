"""Tests for the webhook client (payload construction, retries, failure)."""

from __future__ import annotations

from pathlib import Path

import requests

from src.webhook_client import build_payload, send_report

METRICS = {
    "total_revenue": 1234.56,
    "total_orders": 42,
    "total_units": 87,
    "period_start": "2026-01-01",
    "period_end": "2026-06-30",
}


class _Response:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class _FakeSession:
    """Captures request kwargs; configurable to fail a number of times."""

    def __init__(self, fail_count: int = 0, error: Exception | None = None):
        self.fail_count = fail_count
        self.error = error
        self.calls: list[dict] = []

    def post(self, url, data=None, files=None, timeout=None):
        self.calls.append({"url": url, "data": data, "files": files, "timeout": timeout})
        if self.error is not None:
            raise self.error
        if len(self.calls) <= self.fail_count:
            return _Response(500, "boom")
        return _Response(200, "ok")


def test_build_payload_contains_metadata(config, tmp_path: Path):
    report = tmp_path / "sales_report.xlsx"
    report.write_bytes(b"placeholder")
    payload = build_payload(config, report, METRICS)
    assert payload["status"] == "success"
    assert payload["report_name"] == "sales_report.xlsx"
    assert payload["total_revenue"] == 1234.56
    assert payload["total_orders"] == 42
    assert payload["company_name"] == "Northstar Commerce"
    assert "generated_at" in payload


def test_send_report_success_includes_attachment(config, tmp_path: Path):
    config.webhook_max_attempts = 1
    report = tmp_path / "sales_report.xlsx"
    report.write_bytes(b"fake-excel-bytes")
    session = _FakeSession()
    result = send_report(config, report, METRICS, session=session)
    assert result.success is True
    assert result.status_code == 200
    assert session.calls[0]["files"] is not None
    assert "report" in session.calls[0]["files"]
    assert session.calls[0]["data"]["status"] == "success"


def test_send_report_retries_then_fails(config, tmp_path: Path):
    config.webhook_max_attempts = 3
    config.webhook_backoff_base = 0  # no real sleeping in tests
    report = tmp_path / "sales_report.xlsx"
    report.write_bytes(b"fake-excel-bytes")
    session = _FakeSession(error=requests.exceptions.ConnectionError("down"))
    result = send_report(config, report, METRICS, session=session)
    assert result.success is False
    assert result.attempts == 3
    assert len(session.calls) == 3
    assert "down" in result.message


def test_send_report_stops_on_success_after_retry(config, tmp_path: Path):
    config.webhook_max_attempts = 3
    config.webhook_backoff_base = 0
    report = tmp_path / "sales_report.xlsx"
    report.write_bytes(b"fake-excel-bytes")
    session = _FakeSession(fail_count=1)  # first call 500, second succeeds
    result = send_report(config, report, METRICS, session=session)
    assert result.success is True
    assert result.attempts == 2
    assert len(session.calls) == 2
