# Automated Excel Sales Reporting System

A production-quality portfolio project demonstrating how a repetitive, manual Excel
reporting workflow can be fully automated with **Python** and **n8n**.

## Overview

Small and medium businesses routinely export sales data into Excel files, then spend
hours every week manually opening each file, combining them, cleaning inconsistent
data, calculating metrics, formatting a report, and emailing it to management.

This project automates that entire workflow for a fictional e-commerce company,
**Northstar Commerce**. The Python application discovers monthly sales files, validates
and cleans them, combines the data, computes business metrics, builds a professional
multi-sheet Excel report **with charts**, and uploads the finished report to an **n8n**
workflow that emails it to management.

The only remaining manual step is the email delivery, which is handled by n8n on purpose:
Python does the heavy data/reporting lifting, n8n handles notification.

## Business Scenario

Northstar Commerce is a small e-commerce company selling electronics and office
equipment across several regions. Every month the sales team exports one Excel file
per export batch. The current manual workflow:

1. Sales employees export Excel files.
2. Someone opens each file by hand.
3. Files are combined manually.
4. Inconsistent data is fixed by hand.
5. Revenue and sales metrics are calculated in spreadsheets.
6. Summary tables and charts are built.
7. The final report is saved and emailed to management.

This project automates steps 2-8 (and triggers step 9 via n8n).

## What the Automation Does

```
Excel files
    ↓
Python discovers files
    ↓
Validate input files
    ↓
Load data
    ↓
Clean and normalize data
    ↓
Combine datasets
    ↓
Calculate metrics
    ↓
Generate professional Excel report
    ↓
Save report
    ↓
Send webhook to n8n (multipart/form-data with the actual file)
    ↓
n8n emails the report
```

## Architecture

```
                  ┌────────────────────────────────────────────┐
                  │  data/input/*.xlsx  (6 monthly files)      │
                  └──────────────────────┬─────────────────────┘
                                         ▼
   ┌─────────────────────────  PYTHON PIPELINE  ─────────────────────────┐
   │  data_loader → data_validator → data_cleaner → analytics            │
   │        → report_generator (9-sheet .xlsx with charts)               │
   └─────────────────────────────────┬────────────────────────────────────┘
                                     │  POST multipart/form-data
                                     │  (file part "report" + JSON metadata)
                                     ▼
                          ┌───────────────────────┐
                          │       n8n             │
                          │ Webhook → Email node  │
                          └───────────────────────┘
                                     │
                                     ▼
                          Management inbox receives
                          the Excel report attached
```

**Why this split?** Sending a local filesystem path to a remote n8n server does not
work. Python therefore uploads the *actual file* as `multipart/form-data`, and n8n
attaches that file to the email. Python never needs SMTP credentials; n8n owns them.

## Features

- **Automatic file discovery**: no hardcoded filenames; every `.xlsx` in `data/input` is processed.
- **Validation**: required columns, data types, dates, quantities, prices, discounts, order statuses; warnings vs. errors are distinguished and logged.
- **Cleaning pipeline**: duplicate removal, whitespace trimming, capitalization and category/region normalization, missing-value repair, date normalization, and quarantine of invalid rows.
- **Business analytics**: total/gross revenue, discounts, order counts, units sold, average order value, customers, products, cancellation rate, month-over-month growth, and breakdowns by month, category, product, salesperson, region, payment method, plus top-10 lists.
- **Professional Excel report**: 9 worksheets with KPIs, 4 charts, number/currency/percent formats, freeze panes, autofilters, and conditional formatting.
- **Data Quality worksheet**: shows exactly what was found and fixed.
- **Logging**: console + rotating file (`logs/automation.log`).
- **n8n integration**: the report is uploaded to a webhook that emails it; retries with exponential backoff; the local report is never deleted on failure.
- **Configuration & security**: everything configurable via `config.yaml` + `.env`; no secrets committed.
- **Tests**: 33 pytest tests covering cleaning, validation, analytics, report generation and webhook payloads.

## Tech Stack

- Python 3.11+
- pandas (data processing)
- openpyxl (Excel read + write + charts)
- requests (webhook)
- PyYAML (configuration)
- python-dotenv (environment variables)
- pytest (testing)

## Project Structure

```
.
├── config.yaml              # runtime configuration
├── requirements.txt
├── run.py                   # CLI entry point
├── data/
│   ├── input/               # monthly sales Excel files (auto-generated)
│   └── processed/           # (reserved for cleaned/combined artifacts)
├── reports/                 # generated sales_report_YYYY-MM-DD.xlsx
├── logs/                    # automation.log
├── src/
│   ├── __init__.py
│   ├── main.py              # pipeline orchestrator
│   ├── config.py            # config loading + env overrides
│   ├── models.py            # dataclasses (ValidationResult, CleaningReport, ...)
│   ├── constants.py         # column names + normalization maps
│   ├── dates.py             # robust mixed-format date parsing
│   ├── logger.py            # logging setup
│   ├── data_loader.py       # discovery + loading
│   ├── data_validator.py    # validation rules
│   ├── data_cleaner.py      # cleaning pipeline
│   ├── analytics.py         # metrics + breakdowns
│   ├── report_generator.py  # 9-sheet Excel report with charts
│   └── webhook_client.py    # n8n delivery (multipart, retry, backoff)
├── scripts/
│   ├── generate_sample_data.py
│   └── send_webhook_only.py   # deliver the latest report to n8n without a full rerun
├── tests/                   # pytest suite
└── n8n/
    ├── workflow.json        # importable n8n workflow
    └── README.md            # n8n setup guide
```

## Installation

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (cmd)
.venv\Scripts\activate.bat
# Linux / macOS
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Generate Sample Data

The input files are generated by a script (no need to hand-write Excel files):

```powershell
python run.py --generate-data
# or, for reproducibility:
python run.py --generate-data --seed 42
```

This creates six files in `data/input/`:

```
sales_2026_01.xlsx  ...  sales_2026_06.xlsx   (100-300 rows each)
```

Each workbook contains realistic transactions: order IDs, dates, customers, products,
categories, quantities, prices, discounts, salespeople, regions, payment methods and
order statuses.

The generated data is **intentionally messy**. A small percentage of rows contain
realistic problems so the validation and cleaning pipeline can be demonstrated
(see [Data Quality](#data-quality)).

## Configuration

### `config.yaml`

Everything the pipeline needs at runtime:

```yaml
app:            # company name, currency
paths:          # input/output/log folders
report:         # filename pattern, include raw data sheet
logging:        # level, rotation
validation:     # allowed order statuses, max discount
webhook:        # enabled, url placeholder, timeout, retries
```

### `.env` (secrets, never committed)

```env
N8N_WEBHOOK_URL=https://your-n8n-host.example.com/webhook/sales-report
REPORT_RECIPIENT_EMAIL=management@your-company.com
```

Copy `.env.example` to `.env` and fill in the real values. The webhook URL is read
from the environment, so secrets never live in `config.yaml` or the repository.

## Running the Automation

```powershell
# Full run (generates the report and emails it via n8n)
python run.py

# Build the report without sending email (no n8n needed)
python run.py --no-webhook

# Override folders
python run.py --input data/input --output reports

# Custom config
python run.py --config my-config.yaml
```

If you already generated a report and just want to re-deliver the latest one to n8n
(no reloading, cleaning, or rebuilding), use:

```powershell
python scripts\send_webhook_only.py
```

A successful run prints a summary:

```
PIPELINE COMPLETE
Input files processed : 6
Rows loaded          : 1274
Rows in final report : 1245 (duplicates removed=11, invalid removed=18)
Total revenue        : 416158.16
Total orders         : 1161
Average order value  : 358.45
Cancellation rate    : 6.67%
Report               : C:\...\reports\sales_report_2026-08-07.xlsx
Webhook delivery     : SUCCESS (attempts=1)
```

Full details are written to `logs/automation.log`.

## n8n Setup

The `n8n/` folder contains an importable workflow and a complete guide. In short:

1. Import `n8n/workflow.json` into n8n (Workflows → Import from File).
2. Configure the **Send Email** node with your SMTP credentials (Gmail, SendGrid, Mailgun, or company SMTP).
3. Activate the workflow.
4. Copy the webhook URL from the Webhook node (e.g. `https://your-n8n-host.example.com/webhook/sales-report`).
5. Put that URL in `.env` as `N8N_WEBHOOK_URL`.
6. Run `python run.py`.

See [n8n/README.md](n8n/README.md) for step-by-step instructions and troubleshooting.

## Example Output

The generated workbook `reports/sales_report_YYYY-MM-DD.xlsx` contains nine sheets:

| Sheet | Contents |
| --- | --- |
| **Dashboard** | KPI cards (revenue, orders, AOV, units, customers, cancellation rate) + 4 charts (monthly revenue trend, revenue by category, revenue by region, top 10 products) |
| **Executive Summary** | Key metrics, report info, business highlights |
| **Monthly Performance** | Per-month orders/units/revenue/discounts and month-over-month growth with a color scale |
| **Product Performance** | Per-product revenue, units and share, with data bars |
| **Salesperson Performance** | Revenue per salesperson |
| **Regional Performance** | Revenue per region |
| **Customer Performance** | Top 10 customers |
| **Data Quality** | Files processed, rows loaded, duplicates/invalid/missing handled, rows included vs. excluded, and validation warnings |
| **Raw Data** | The cleaned, normalized transactions with calculated revenue fields |

## Data Quality

Real business data is messy, and the sample generator intentionally reproduces common
problems in a small percentage of records:

- exact duplicate rows
- missing customer names
- extra whitespace
- inconsistent capitalization
- inconsistent category names (`electronics`, `Electronics `, ...)
- inconsistent region names (`north america`, `APAC`, `Europe `, ...)
- missing discounts
- inconsistent date formats (`2026-01-15`, `15/01/2026`, `2026.01.15`, ...)
- invalid quantities (negative or non-numeric)
- invalid prices (negative)

The pipeline handles these deterministically:

- **Duplicates** are removed (count recorded).
- **Whitespace** is trimmed; **names/categories/regions** are normalized to a canonical form.
- **Missing discounts** become 0; **missing customer names** become `Unknown Customer`.
- **Dates** are parsed into proper datetime values regardless of source format.
- **Invalid records** (bad quantities/prices/dates/statuses) are quarantined and excluded,
  never silently passed through.
- **Cancelled/refunded orders** are kept for transparency but excluded from revenue.
- Calculated fields are added: `Gross Revenue = Qty × Price`, `Discount Amount`,
  `Net Revenue`.

Every decision is logged and summarized on the **Data Quality** worksheet.

## Testing

```powershell
python -m pytest
```

The suite covers:

- cleaning: duplicates, whitespace, missing values, normalization, invalid-row removal, calculated fields
- analytics: revenue (cancellation excluded), order values, cancellation rate, month-over-month growth (incl. division by zero), breakdowns
- validation: pass/fail for columns, types, dates, statuses, discounts
- report generation: all 9 sheets, KPI values, Data Quality content, raw data rows, charts
- webhook: payload construction, successful delivery with attachment, retry/backoff, final failure

## Architecture Decisions

- **Why Python for data + reporting?** Python (pandas + openpyxl) is the right tool for
  reading many Excel files, cleaning messy data, computing metrics, and programmatically
  formatting a professional workbook. Doing this in n8n would be verbose and fragile.
- **Why n8n for email?** Sending email requires SMTP credentials and templates. Keeping
  that in n8n (a workflow tool built for exactly this) separates credentials from the
  data pipeline and makes the email step editable without touching code.
- **Why multipart/form-data?** A remote n8n server cannot open a file on the Python
  machine. Uploading the actual file as `multipart/form-data` is the technically correct
  integration.
- **Why openpyxl (not XlsxWriter)?** XlsxWriter cannot read existing workbooks; openpyxl
  supports both reading and writing and native chart support.

## Possible Production Improvements

These are realistic next steps **not implemented here**:

- **Database integration**: store raw/cleaned data in SQLite/Postgres instead of a combined DataFrame.
- **Scheduled execution**: run via cron / Windows Task Scheduler / GitHub Actions on a weekly cadence.
- **Cloud storage**: archive reports in S3 / Azure Blob / Google Cloud Storage instead of local disk.
- **Authentication**: protect the n8n webhook (basic auth, webhook path secret, or n8n's static bearer token).
- **Monitoring & alerting**: send pipeline failure notifications (email, Slack) and expose metrics.
- **Docker**: containerize the pipeline and the n8n instance for reproducible deployment.
- **API integration**: pull orders from an ERP/e-commerce API (Shopify, WooCommerce, etc.) instead of Excel.
- **Cloud deployment**: run on a VM / serverless function with managed scheduling.
- **Configurable date parsing**: make the day-first vs. month-first ambiguity configurable.

## Portfolio Highlights

- **Automates a real repetitive workflow**: the entire manual "combine → clean → calculate → format → email" loop is replaced by one command.
- **Robust data cleaning**: the pipeline validates, repairs and normalizes messy data instead of blindly copying it.
- **Professional reporting**: a 9-sheet workbook with KPIs, charts, formatting, and conditional formatting that looks like a genuine business report.
- **Automated business metrics**: revenue, AOV, cancellation rate, growth trends, and breakdowns are computed reliably.
- **Real integration**: the report is uploaded to n8n and emailed, demonstrating end-to-end automation (no fake local-path shortcuts).
- **Engineered for the real world**: logging, configuration, error handling, retries with backoff, and a Data Quality worksheet show production thinking.
- **Configurable**: folders, currency, file patterns and webhook behavior are all controlled by `config.yaml` and `.env`.

> Note: this project does not claim a specific number of hours saved. For many small
> businesses, a similar workflow takes an employee 2-4 hours per week; automating it
> removes the manual effort entirely, which is the core business value.
