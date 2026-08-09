# n8n Workflow: Sales Report Email

This workflow receives the Excel report uploaded by the Python pipeline and emails it
to management. It is designed so that **you only need to configure your own SMTP
credentials**; no secrets are stored in the workflow file.

## How it works

1. **Webhook** (`POST /webhook/sales-report`) receives the request from Python.
   The report arrives as `multipart/form-data`:
   - a file part named `report` (the Excel workbook), exposed as binary data under `$binary.report`
   - JSON metadata fields (status, report_name, period_start, period_end, total_revenue, total_orders, ...), exposed under `$json`
2. **Send Email** builds the email using expressions on the metadata (`{{ $json[...] }}`)
   and attaches the binary part `report`.
3. **Respond to Webhook** returns `{"success": true, ...}` to Python, so the pipeline
   can confirm delivery.

## Setup instructions

### 1. Import the workflow

1. Log in to your n8n instance (cloud or self-hosted).
2. Go to **Workflows** > **⋮ (menu)** > **Import from File**.
3. Select `n8n/workflow.json`.
4. The workflow "Northstar Commerce - Sales Report Email" appears in the editor.

### 2. Configure the webhook

The webhook node is pre-configured:
- **HTTP Method**: `POST`
- **Path**: `sales-report`
- **Respond**: "Using 'Respond to Webhook' Node"

If you change the path, remember to update the URL you put in `.env`.

### 3. Configure email (SMTP) credentials

1. Open the **Send Email** node.
2. In the *Credential for SMTP Account* dropdown, choose **Create New Credential** (or **Connect existing credential**).
3. Enter your SMTP host, port, user and password (for example Gmail app password, SendGrid, Mailgun, or your company SMTP).
4. Change `fromEmail` to your real sender address and set the recipient via `toEmail`
   (it already falls back to `management@northstar-commerce.example` if the payload
   has no `report_recipient_email`).
5. Save.

### 4. Activate the workflow

Toggle **Active** (top right) to **on**. A green webhook URL appears under the Webhook node.

### 5. Copy the webhook URL

Copy the full URL, e.g. `https://your-n8n-host.example.com/webhook/sales-report`.

### 6. Add it to the Python environment

1. Copy `.env.example` to `.env`.
2. Set `N8N_WEBHOOK_URL=https://your-n8n-host.example.com/webhook/sales-report`.
3. Optionally set `REPORT_RECIPIENT_EMAIL=management@your-company.com`.

### 7. Test the complete workflow

1. Generate sample data and run the pipeline:

   ```powershell
   python run.py --generate-data
   python run.py
   ```

2. Watch the console output. A successful run ends with:

   ```
   Webhook delivery     : SUCCESS (attempts=1)
   ```

3. In n8n, open the **Executions** panel to see the run; the email should arrive in
   the configured inbox with the Excel report attached.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Webhook delivery FAILED ... HTTP 404` | Wrong webhook path or workflow not active. Copy the exact URL from the Webhook node. |
| `HTTP 401/403` | Your n8n instance requires auth on webhooks; use the workflow URL that includes the path only (no /webhook-test) and ensure the workflow is Active. |
| Email node error "No credentials" | Open the Send Email node and connect/create the SMTP credential. |
| Attachment missing | Ensure the multipart file field is named exactly `report` (that is what the Python client sends). |
| Workflow import fails | Use n8n 1.x+. Older 0.x instances need manual rebuild. |

## Note on local testing

Python and n8n run in the same demo environment? If n8n runs on `localhost`, point
`N8N_WEBHOOK_URL` to `http://localhost:5678/webhook/sales-report`. If you want to try
the webhook without email, temporarily connect the Webhook node to a **Respond to
Webhook** node only (skip Send Email) — the pipeline still confirms delivery.
