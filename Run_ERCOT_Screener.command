#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

fail_python_version() {
  echo "This launcher requires Python 3.12.x."
  echo "Install python3.12 and recreate .venv before running the app."
  exit 1
}

if [[ -d ".venv" ]]; then
  if ! .venv/bin/python - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)
PY
  then
    fail_python_version
  fi
else
  if ! command -v python3.12 >/dev/null 2>&1; then
    fail_python_version
  fi
  python3.12 -m venv .venv
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

METRICS_SCHEMA_OK="$("$PYTHON_BIN" - <<'PY'
from pathlib import Path

import pandas as pd

from src.config import LENS_KEYS, SETTINGS, lens_metric_column

path = SETTINGS.metrics_path(SETTINGS.target_year)
if not Path(path).exists():
    print("0")
    raise SystemExit

required = {"location", "location_type", "best_fit_lens", "best_fit_rank", "observations"}
for profile_key, duration_hours in LENS_KEYS:
    required.update(
        {
            lens_metric_column(profile_key, duration_hours, "rank"),
            lens_metric_column(profile_key, duration_hours, "score"),
            lens_metric_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh"),
            lens_metric_column(profile_key, duration_hours, "annual_cost_reduction_pct"),
        }
    )

frame = pd.read_parquet(path)
print("1" if required.issubset(frame.columns) else "0")
PY
)"

if [[ ! -f "$PROCESSED_PATH" ]]; then
  "$PYTHON_BIN" -m src.data.fetch
fi

if [[ ! -f "$METRICS_PATH" || ! -f "$DAILY_PROFILE_WINDOWS_PATH" || ! -f "$HOURLY_PROFILE_SHAPE_PATH" || "$METRICS_SCHEMA_OK" != "1" ]]; then
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
