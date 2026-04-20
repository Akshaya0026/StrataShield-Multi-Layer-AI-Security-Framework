#!/usr/bin/env bash
# start_backend.sh — Starts the StrataShield Security Engine (FastAPI)
# Usage: bash start_backend.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$SCRIPT_DIR/backend"

echo "═══════════════════════════════════════════════"
echo "  StrataShield — Security Engine Startup"
echo "═══════════════════════════════════════════════"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 not found. Please install Python 3.9+."
  exit 1
fi

# Install dependencies if needed
echo "📦 Installing Python dependencies…"
pip3 install -r "$BACKEND/requirements.txt" -q

# Train model if it doesn't exist
if [ ! -f "$BACKEND/model.pkl" ]; then
  echo "🧠 Training Isolation Forest model…"
  python3 "$BACKEND/train_model.py"
fi

echo "🚀 Starting FastAPI Security Engine on http://localhost:8000"
cd "$BACKEND"
python3 -m uvicorn security_engine:app --reload --host 0.0.0.0 --port 8000
