#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root (adjust if needed)
cd "$(dirname "$0")/.."

# --- VENV SETUP ---
if [ ! -d "venv" ]; then
  echo "[INFO] Creating venv..."
  python3 -m venv venv
fi
source venv/bin/activate
python -m pip install -U pip setuptools wheel >/dev/null

# --- DEPS ---
# Make sure fastapi/uvicorn + OTel distro are installed
python -m pip show fastapi >/dev/null 2>&1 || pip install fastapi uvicorn requests
python -m pip show opentelemetry-distro >/dev/null 2>&1 || \
  pip install "opentelemetry-distro[otlp]"

# --- OTEL CONFIG (gRPC) ---
export OTEL_SERVICE_NAME=${OTEL_SERVICE_NAME:-demo-app}
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT:-localhost:4317}
export OTEL_EXPORTER_OTLP_INSECURE=true

echo "[INFO] Starting $OTEL_SERVICE_NAME with OTel gRPC exporter"
echo "       Endpoint: $OTEL_EXPORTER_OTLP_ENDPOINT"

# --- START APP ---
exec opentelemetry-instrument \
  --traces_exporter otlp \
  --metrics_exporter otlp \
  --logs_exporter otlp \
  --service_name "$OTEL_SERVICE_NAME" \
  uvicorn app:app --host 0.0.0.0 --port 8080

