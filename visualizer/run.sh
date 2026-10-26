#!/bin/bash
set -eo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SCRIPT_SOURCE" ]; do
    SCRIPT_DIR="$( cd -P "$( dirname "$SCRIPT_SOURCE" )" >/dev/null 2>&1 && pwd )"
    SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
    [[ $SCRIPT_SOURCE != /* ]] && SCRIPT_SOURCE="$SCRIPT_DIR/$SCRIPT_SOURCE"
done
VIS_DIR="$( cd -P "$( dirname "$SCRIPT_SOURCE" )" >/dev/null 2>&1 && pwd )"
REPO_ROOT="$(cd "$VIS_DIR/.." && pwd)"

PORT="${PORT:-5000}"
HOST="${HOST:-127.0.0.1}"
DEV_MODE=0
FORCE_BUILD=0
OPEN_BROWSER=1

print_usage() {
    cat << EOF
Alphable Visualizer Studio Launcher

Usage:
  ./visualizer/run.sh [OPTIONS]

Options:
  --dev           Run React development server (port 3000) alongside Flask backend (port 5000)
  --build         Rebuild React frontend bundle before starting
  --no-browser    Do not automatically open default browser
  --port <port>   Specify backend port (default: 5000)
  --host <host>   Specify backend host (default: 127.0.0.1)
  -h, --help      Show this help message

Default mode:
  Serves compiled React frontend directly from Flask backend at http://localhost:5000.
  Zero Node.js runtime overhead, instant startup, single process.
EOF
}

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            DEV_MODE=1
            shift
            ;;
        --build)
            FORCE_BUILD=1
            shift
            ;;
        --no-browser)
            OPEN_BROWSER=0
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Step 1: Activate Virtual Environment
if [ -d "$REPO_ROOT/venv" ]; then
    echo "✓ Activating workspace virtual environment..."
    source "$REPO_ROOT/venv/bin/activate"
elif [ -d "$VIS_DIR/venv" ]; then
    echo "✓ Activating local virtual environment..."
    source "$VIS_DIR/venv/bin/activate"
else
    echo "⚠️ Warning: No virtual environment found. Using system python."
fi

# Set PYTHONPATH to repository root
export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"

# Step 2: Check / Build Frontend Bundle
FRONTEND_BUILD="$VIS_DIR/frontend/build"
if [ "$FORCE_BUILD" -eq 1 ] || [ ! -d "$FRONTEND_BUILD" ]; then
    echo "Building React frontend production bundle..."
    cd "$VIS_DIR/frontend"
    npm run build
    cd "$VIS_DIR"
fi

# Step 3: Open browser if requested
open_url() {
    local url="$1"
    sleep 1.2
    if [ "$OPEN_BROWSER" -eq 1 ]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url" &> /dev/null &
        elif command -v open &> /dev/null; then
            open "$url" &> /dev/null &
        fi
    fi
}

# Step 4: Launch Server
if [ "$DEV_MODE" -eq 1 ]; then
    echo "🚀 Starting in DEVELOPMENT mode (React on :3000, Flask on :$PORT)..."
    open_url "http://localhost:3000"
    (cd "$VIS_DIR/frontend" && npm start) &
    REACT_PID=$!
    trap "kill $REACT_PID 2>/dev/null || true" EXIT
    python "$VIS_DIR/backend/app.py"
else
    echo "🚀 Starting Alphable Visualizer Studio on http://$HOST:$PORT ..."
    open_url "http://$HOST:$PORT"
    export PORT="$PORT"
    export HOST="$HOST"
    python "$VIS_DIR/backend/app.py"
fi
