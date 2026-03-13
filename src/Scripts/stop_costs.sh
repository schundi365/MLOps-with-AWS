#!/bin/bash
# Quick script to stop all costly AWS resources
# Usage: ./stop_costs.sh [--dry-run]

set -e

REGION="${AWS_REGION:-us-east-1}"
DRY_RUN=""

# Parse arguments
if [ "$1" == "--dry-run" ]; then
    DRY_RUN="--dry-run"
    echo "Running in DRY-RUN mode..."
fi

# Check if Python script exists
if [ ! -f "stop_all_costly_resources.py" ]; then
    echo "Error: stop_all_costly_resources.py not found"
    exit 1
fi

# Run the Python script
echo "Stopping costly AWS resources in region: $REGION"
python stop_all_costly_resources.py --region "$REGION" $DRY_RUN

echo ""
echo "Done!"
