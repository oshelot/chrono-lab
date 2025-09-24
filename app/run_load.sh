#!/usr/bin/env bash
set -euo pipefail
URL="${1:-http://localhost:8080/chat}"
DUR="${2:-2}"
RPS="${3:-6}"
CONC="${4:-4}"
shift || true

echo "[INFO] loadgen chat -> $URL | ${DUR}m | 1..${RPS} rps | conc=${CONC}"
python3 loadgen.py --mode chat --url "$URL" --duration "$DUR" --max-rps "$RPS" --concurrency "$CONC" "$@"
