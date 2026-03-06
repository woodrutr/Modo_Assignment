#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
CHECK_ONLY="${CHECK_ONLY:-0}"

on_error() {
  echo ""
  echo "Startup failed."
  echo "Press Return to close this window."
  read
}

trap on_error ERR

echo "Repository root: $ROOT_DIR"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Creating local virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_PYTHON" -c "import gridstatus, pandas, pyarrow, streamlit" >/dev/null 2>&1; then
  echo "Installing pinned dependencies..."
  "$VENV_PIP" install -r "$ROOT_DIR/requirements.txt"
fi

processed_artifacts=("$ROOT_DIR"/data/processed/ercot_dam_spp_utc_*.parquet(N))

if (( ${#processed_artifacts} == 0 )); then
  echo "No processed ERCOT artifacts found. Fetching data..."
  "$VENV_PYTHON" -m src.data.fetch
fi

echo "Building metric artifacts..."
"$VENV_PYTHON" -m src.analytics.metrics

if [[ "$CHECK_ONLY" == "1" ]]; then
  echo "CHECK_ONLY=1 set. Bootstrap completed without launching Streamlit."
  exit 0
fi

if [[ "$OPEN_BROWSER" == "1" ]]; then
  (
    sleep 3
    open "http://127.0.0.1:8501"
  ) &
fi

echo "Launching Streamlit app..."
exec "$STREAMLIT_BIN" run "$ROOT_DIR/app.py" --server.address 127.0.0.1 --server.port 8501
