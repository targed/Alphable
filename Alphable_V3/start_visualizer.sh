#!/bin/bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-5000}"
HOST="${HOST:-127.0.0.1}"
DEV_MODE=0
FORCE_BUILD=0
OPEN_BROWSER=1
STOP_ONLY=0

print_usage() {
    cat << EOF
Alphable Replay Visualizer Launcher

Usage:
  ./start_visualizer.sh [OPTIONS]

Options:
  --dev           Run React development server (port 3000) alongside Flask backend (port 5000)
  --build         Rebuild React frontend production bundle before starting
  --stop          Stop any currently running visualizer processes and exit
  --no-browser    Do not automatically open the visualizer in the default browser
  --port <port>   Specify backend port (default: 5000)
  --host <host>   Specify backend host (default: 127.0.0.1)
  -h, --help      Show this help message

Default mode:
  Serves compiled React frontend directly from Flask backend at http://localhost:5000.
  Zero Node.js runtime overhead, instant startup, and no port collisions.
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
        --stop)
            STOP_ONLY=1
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

# Function to free port
kill_port_process() {
    local target_port="$1"
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${target_port}/tcp" 2>/dev/null || true
    elif command -v lsof >/dev/null 2>&1; then
        local pids
        pids=$(lsof -ti :"${target_port}" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi
    fi
}

# Handle --stop
if [ "$STOP_ONLY" -eq 1 ]; then
    echo "Stopping any running visualizer processes on port $PORT and 3000..."
    kill_port_process "$PORT"
    kill_port_process 3000
    pkill -f "visualizer/backend/app.py" 2>/dev/null || true
    echo "Visualizer stopped."
    exit 0
fi

echo "=========================================="
echo "    Alphable Replay Visualizer Launcher   "
echo "=========================================="
echo ""

# Find Python executable
PYTHON_BIN=""
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [ -x "$ROOT_DIR/../venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/../venv/bin/python"
elif [ -x "$ROOT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/venv/bin/python"
else
    echo "Error: Python virtual environment not found."
    echo "Searched: \$VIRTUAL_ENV, ../venv, and ./venv"
    exit 1
fi

echo "✓ Python: $PYTHON_BIN"

# Check Node.js and npm if build or dev mode needed
if [ ! -d "visualizer/frontend/node_modules" ] || [ "$DEV_MODE" -eq 1 ] || [ "$FORCE_BUILD" -eq 1 ] || [ ! -f "visualizer/frontend/build/index.html" ]; then
    if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
        echo "Error: Node.js and npm are required to build/run the frontend."
        exit 1
    fi
fi

# Ensure node_modules exist
if [ ! -d "visualizer/frontend/node_modules" ]; then
    echo "Installing frontend dependencies (npm install)..."
    (cd visualizer/frontend && npm install)
fi

# Build frontend if needed or requested
if [ "$FORCE_BUILD" -eq 1 ] || { [ "$DEV_MODE" -eq 0 ] && [ ! -f "visualizer/frontend/build/index.html" ]; }; then
    echo "Compiling frontend production bundle..."
    (cd visualizer/frontend && npm run build)
fi

# Clean up stale processes on target port
echo "Checking port $PORT..."
kill_port_process "$PORT"
if [ "$DEV_MODE" -eq 1 ]; then
    kill_port_process 3000
fi
sleep 0.5

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down visualizer..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    kill_port_process "$PORT"
    if [ "$DEV_MODE" -eq 1 ]; then
        kill_port_process 3000
    fi
    echo "Visualizer shut down cleanly."
}

trap cleanup EXIT INT TERM

# Start Backend
BACKEND_LOG=$(mktemp /tmp/alphable_visualizer_backend.XXXXXX.log)
echo "Starting Flask backend on http://$HOST:$PORT ..."
PORT="$PORT" HOST="$HOST" "$PYTHON_BIN" "$ROOT_DIR/visualizer/backend/app.py" > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# Health check polling (up to 20 seconds)
echo -n "Waiting for backend to initialize"
READY=0
for i in {1..40}; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo "Error: Backend process terminated unexpectedly. Logs:"
        cat "$BACKEND_LOG"
        exit 1
    fi

    if curl -s -f "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
        READY=1
        break
    fi
    echo -n "."
    sleep 0.5
done
echo ""

if [ "$READY" -ne 1 ]; then
    echo "Error: Backend health check timed out after 20 seconds. Logs:"
    cat "$BACKEND_LOG"
    exit 1
fi

echo "✓ Backend online at http://$HOST:$PORT"

# Open browser helper
open_url() {
    local url="$1"
    if [ "$OPEN_BROWSER" -eq 1 ]; then
        if command -v xdg-open >/dev/null 2>&1; then
            xdg-open "$url" >/dev/null 2>&1 &
        elif command -v open >/dev/null 2>&1; then
            open "$url" >/dev/null 2>&1 &
        fi
    fi
}

if [ "$DEV_MODE" -eq 1 ]; then
    echo "Starting React dev server on http://localhost:3000 ..."
    echo "Press Ctrl+C to stop both backend and frontend."
    echo ""
    cd visualizer/frontend
    BROWSER=none npm start &
    FRONTEND_PID=$!
    cd "$ROOT_DIR"

    # Wait briefly for React dev server port, then open browser
    for i in {1..30}; do
        if curl -s "http://localhost:3000" >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
    open_url "http://localhost:3000"
    wait "$FRONTEND_PID"
else
    echo "Serving compiled visualizer at http://$HOST:$PORT"
    echo "Press Ctrl+C to stop the visualizer."
    echo ""
    open_url "http://localhost:$PORT"
    # Wait on backend process
    wait "$BACKEND_PID"
fi
