#!/usr/bin/env bash
# Enterprise Spark Observability Framework -- daily driver script
# Schedule this via cron/Airflow, e.g. daily at 06:00 for the prior day's apps.
#
# Usage:
#   ./run_observability.sh [YYYY-MM-DD]   (defaults to today)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DATE="${1:-$(date +%F)}"
CONFIG="${SCRIPT_DIR}/config/observability_config.yaml"

echo "[run_observability] run_date=${RUN_DATE} config=${CONFIG}"

spark-submit \
  --master yarn \
  --deploy-mode client \
  --num-executors 4 \
  --executor-memory 4g \
  --executor-cores 2 \
  --conf spark.sql.shuffle.partitions=32 \
  "${SCRIPT_DIR}/cli.py" \
  --config "${CONFIG}" \
  --mode all \
  --run-date "${RUN_DATE}"
