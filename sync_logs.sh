#!/bin/bash
# sync_logs.sh - Continuously mirrors an S3 bucket to the local machine
set -euo pipefail

# Configuration
# Override these at runtime, e.g.:
# AWS_PROFILE=dassie BUCKET_NAME=ap-logs-... ./sync_logs.sh
AWS_PROFILE="${AWS_PROFILE:-dassie}"
BUCKET_NAME="${BUCKET_NAME:-ap-logs-863750994059-us-east-1-steve-test-17}"
LOCAL_DIR="${LOCAL_DIR:-./data/logs}"
SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-5}"

mkdir -p "$LOCAL_DIR"

if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: aws CLI is not installed or not on PATH" >&2
    exit 1
fi

echo "Validating AWS profile and bucket access..."
aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null
aws s3 ls "s3://$BUCKET_NAME/" --profile "$AWS_PROFILE" >/dev/null

echo "Starting continuous sync from s3://$BUCKET_NAME to $LOCAL_DIR..."
echo "Using AWS Profile: $AWS_PROFILE"
echo "Sync interval: ${SYNC_INTERVAL_SECONDS}s"
echo "Press Ctrl+C to stop."

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync cycle started"
    set +e
    sync_output="$(aws s3 sync "s3://$BUCKET_NAME/" "$LOCAL_DIR/" --profile "$AWS_PROFILE" 2>&1)"
    sync_exit_code=$?
    set -e

    if [[ -n "$sync_output" ]]; then
        while IFS= read -r line; do
            [[ -n "$line" ]] && echo "  $line"
        done <<< "$sync_output"
    else
        echo "  No file changes in this cycle"
    fi

    if [[ $sync_exit_code -ne 0 ]]; then
        echo "  Sync failed with exit code: $sync_exit_code"
    fi

    sleep "$SYNC_INTERVAL_SECONDS"
done
