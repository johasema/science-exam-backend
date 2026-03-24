#!/usr/bin/env bash
set -euo pipefail
# Render가 주입하는 PORT (https://render.com/docs/web-services#port-binding)
if [ -z "${PORT:-}" ]; then
  echo "ERROR: PORT is not set. Use Render Web Service or set PORT manually."
  exit 1
fi
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
