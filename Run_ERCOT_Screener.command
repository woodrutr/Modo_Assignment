#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

PYTHON_BIN=".venv/bin/python"
PIP_BIN=".venv/bin/pip"
STREAMLIT_BIN=".venv/bin/streamlit"

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import gridstatus
import pandas
import plotly
import pyarrow
import streamlit
PY
then
  "$PIP_BIN" install -r requirements.txt
fi

TARGET_YEAR="$("$PYTHON_BIN" - <<'PY'
from src.config import SETTINGS
print(SETTINGS.target_year)
PY
)"

PROCESSED_PATH="$("$PYTHON_BIN" - <<'PY'
from src.config import SETTINGS
print(SETTINGS.processed_dam_path(SETTINGS.target_year))
PY
)"

METRICS_PATH="$("$PYTHON_BIN" - <<'PY'
from src.config import SETTINGS
print(SETTINGS.metrics_path(SETTINGS.target_year))
PY
)"

DAILY_PROFILE_WINDOWS_PATH="$("$PYTHON_BIN" - <<'PY'
from src.config import SETTINGS
print(SETTINGS.daily_profile_windows_path(SETTINGS.target_year))
PY
)"

HOURLY_PROFILE_SHAPE_PATH="$("$PYTHON_BIN" - <<'PY'
from src.config import SETTINGS
print(SETTINGS.hourly_profile_shape_path(SETTINGS.target_year))
PY
)"

if [[ ! -f "$PROCESSED_PATH" ]]; then
  "$PYTHON_BIN" -m src.data.fetch
fi

if [[ ! -f "$METRICS_PATH" || ! -f "$DAILY_PROFILE_WINDOWS_PATH" || ! -f "$HOURLY_PROFILE_SHAPE_PATH" ]]; then
  "$PYTHON_BIN" -m src.analytics.metrics --year "$TARGET_YEAR"
fi

if [[ "${CHECK_ONLY:-0}" == "1" ]]; then
  echo "Runner checks passed."
  exit 0
fi

PORT="${PORT:-8501}"
URL="http://127.0.0.1:${PORT}"

if [[ "${OPEN_BROWSER:-1}" == "1" ]]; then
  (
    sleep 3
    open "$URL"
  ) &
fi

exec "$STREAMLIT_BIN" run app.py --server.headless true --server.address 127.0.0.1 --server.port "$PORT"
