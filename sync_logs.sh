#!/bin/bash
# sync_logs.sh - Continuously mirrors an S3 bucket to the local machine

# Configuration
AWS_PROFILE="dassie"
BUCKET_NAME="alpaca-provost-863750994059-us-east-1-an"
LOCAL_DIR="./data/logs"

mkdir -p "$LOCAL_DIR"

echo "Starting continuous sync from s3://$BUCKET_NAME to $LOCAL_DIR..."
echo "Using AWS Profile: $AWS_PROFILE"
echo "Press Ctrl+C to stop."

while true; do
    aws s3 sync "s3://$BUCKET_NAME/" "$LOCAL_DIR/" --profile "$AWS_PROFILE" --quiet
    sleep 5
done
