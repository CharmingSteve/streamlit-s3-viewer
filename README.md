# streamlit-s3-viewer

Local Streamlit dashboard for visualizing Agent Provost logs synced from S3.

## Prerequisites

- macOS or Linux shell
- AWS CLI configured with profile `dassie`
- Python 3.12+

## Bucket Configuration

The sync script supports runtime overrides (recommended):

- `BUCKET_NAME` (no `s3://` prefix)
- `AWS_PROFILE` (defaults to `dassie`)
- `LOCAL_DIR` (defaults to `./data/logs`)

Defaults are defined in [sync_logs.sh](sync_logs.sh), but you should pass the bucket explicitly to avoid stale values.

## Quick Start

From [streamlit-s3-viewer](.) run:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Open terminal 1 and start continuous S3 sync:

```bash
cd /Users/steve/streamlit-s3-viewer
AWS_PROFILE=dassie BUCKET_NAME=ap-logs-863750994059-us-east-1-steve-test-17 ./sync_logs.sh
```

If you need to switch buckets, only change `BUCKET_NAME` in the command:

```bash
cd /Users/steve/streamlit-s3-viewer
AWS_PROFILE=dassie BUCKET_NAME=<your-bucket-name> ./sync_logs.sh
```

Example one-shot manual sync (useful for quick verification):

```bash
cd /Users/steve/streamlit-s3-viewer
aws s3 sync "s3://<your-bucket-name>/" ./data/logs/ --profile dassie --only-show-errors
```

You will see per-cycle output, including downloaded filenames, for example:

```text
[2026-07-13 13:40:33] Sync cycle started
download: s3://.../agent-provost/logs/access/.../A9oUZQbr.json to data/logs/agent-provost/logs/access/.../A9oUZQbr.json
```

Open terminal 2 and start Streamlit:

```bash
cd /Users/steve/streamlit-s3-viewer
source .venv/bin/activate
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open the app at:

- `http://127.0.0.1:8501`

## Verify It Is Running

Use this health check:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
```

Expected output:

- `200`

## How To Get Visualizations

1. Keep [sync_logs.sh](sync_logs.sh) running so fresh JSON logs continue to land under [data/logs](data/logs).
2. Keep Streamlit running from [app.py](app.py).
3. In the browser, use the global UTC time window expander to scope the dataset.
4. Review dashboard sections (KPIs, trends, error distributions, user/symbol activity, request/response drilldowns).
5. Use Streamlit controls already present in the UI to filter and inspect records.

No visualization code changes are required; the app auto-loads from [data/logs](data/logs).

## Stop Services

- Press `Ctrl+C` in the sync terminal.
- Press `Ctrl+C` in the Streamlit terminal.
