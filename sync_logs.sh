#!/bin/bash
# sync_logs.sh - Continuously mirrors an S3 bucket to the local machine
set -euo pipefail

# Configuration
# setting for local laptop agent provost bucket
#BUCKET_NAME="alpaca-provost-863750994059-us-east-1-an"
AWS_PROFILE="dassie"
BUCKET_NAME="ap-logs-863750994059-us-east-1-steve-test-16"
LOCAL_DIR="./data/logs"

mkdir -p "$LOCAL_DIR"

echo "Starting continuous sync from s3://$BUCKET_NAME to $LOCAL_DIR..."
echo "Using AWS Profile: $AWS_PROFILE"
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

    sleep 5
done
