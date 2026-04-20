#!/usr/bin/env bash
# start_dashboard.sh — Starts the StrataShield React Dashboard
# Usage: bash start_dashboard.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$SCRIPT_DIR/frontend"

echo "═══════════════════════════════════════════════"
echo "  StrataShield — Dashboard Startup"
echo "═══════════════════════════════════════════════"

# Check Node
if ! command -v node &>/dev/null; then
  echo "❌ node not found. Please install Node.js 18+."
  exit 1
fi

echo "📦 Installing npm packages (if needed)…"
cd "$FRONTEND"
npm install --silent

echo "🚀 Starting Dashboard on http://localhost:5173"
npm run dev
