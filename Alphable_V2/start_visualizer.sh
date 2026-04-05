#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "Starting Alphable Replay Visualizer..."
echo ""

if [ ! -x "venv/bin/python" ]; then
    echo "Error: project Python environment not found at venv/bin/python"
    echo "Create it first, then install requirements."
    exit 1
fi

# Check if frontend dependencies are installed
if [ ! -d "visualizer/frontend/node_modules" ]; then
    echo "Installing Node.js dependencies..."
    cd visualizer/frontend
    npm install
    cd ../..
fi

BACKEND_PID=""

cleanup() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo "Shutting down backend (pid=$BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

echo "Starting Flask backend on http://localhost:5000 ..."
cd visualizer/backend
"$ROOT_DIR/venv/bin/python" app.py &
BACKEND_PID=$!
cd ../..

sleep 2

echo "Starting React frontend..."
cd visualizer/frontend
npm start
