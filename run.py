"""Command-line entry point for the Automated Excel Sales Reporting System.

Usage examples::

    python run.py --generate-data          # create sample input files
    python run.py --no-webhook             # build the report without emailing
    python run.py --input data/input --output reports
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Config
from src.exceptions import PipelineError
from src.logger import setup_logging

VERSION = "1.0.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Automated Excel Sales Reporting System for Northstar Commerce.",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML config file (default: config.yaml)")
    parser.add_argument("--input", default=None, help="Override the input folder (default: from config.yaml)")
    parser.add_argument("--output", default=None, help="Override the output/report folder (default: from config.yaml)")
    parser.add_argument("--no-webhook", action="store_true", help="Disable the n8n webhook even if configured")
    parser.add_argument("--no-email", action="store_true", help="Disable direct SMTP email even if configured")
    parser.add_argument("--generate-data", action="store_true", help="Generate sample data into data/input then exit")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sample data generation (default: 42)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def _print_summary(result) -> None:
    print("\n" + "=" * 62)
    print("PIPELINE COMPLETE")
    print("=" * 62)
    metrics = result.analytics.metrics
    print(f"Input files processed : {len([f for f in result.files_processed if f.status == 'ok'])}")
    print(f"Rows loaded          : {result.cleaning.rows_before}")
    print(f"Rows in final report : {result.cleaning.rows_final} "
          f"(duplicates removed={result.cleaning.duplicate_rows_removed}, "
          f"invalid removed={result.cleaning.invalid_rows_removed})")
    print(f"Total revenue        : {metrics['total_revenue']:.2f}")
    print(f"Total orders         : {metrics['total_orders']}")
    print(f"Average order value  : {metrics['avg_order_value']:.2f}")
    print(f"Cancellation rate    : {metrics['cancellation_rate']:.2f}%")
    print(f"Report               : {result.report_path}")
    if result.webhook is not None:
        status = "SUCCESS" if result.webhook.success else "FAILED"
        print(f"Webhook delivery     : {status} (attempts={result.webhook.attempts})")
        if not result.webhook.success:
            print(f"  Note: report is still available locally at {result.report_path}")
    else:
        print("Webhook delivery     : disabled")
    if result.email is not None:
        status = "SUCCESS" if result.email.success else "FAILED"
        print(f"Email delivery       : {status} (to={result.email.recipient})")
        if not result.email.success:
            print(f"  Email error: {result.email.message}")
    else:
        print("Email delivery       : disabled")
    print("=" * 62)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.generate_data:
            from scripts import generate_sample_data

            return generate_sample_data.generate(args.seed)

        config = Config.load(config_path=args.config, require_webhook=not args.no_webhook)
        if args.input:
            config.input_folder = Path(args.input)
        if args.output:
            config.output_folder = Path(args.output)
        if args.no_webhook:
            config.webhook_enabled = False
        if args.no_email:
            config.email_enabled = False

        logger = setup_logging(config)
        logger.info("Application started (version %s)", VERSION)

        from src.main import run_pipeline

        result = run_pipeline(config)
        _print_summary(result)
        return 0
    except PipelineError as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        logger = __import__("logging").getLogger("sales_reporting")
        logger.error("Pipeline error: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI safety net
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        traceback.print_exc()
        __import__("logging").getLogger("sales_reporting").exception("Unexpected error")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
