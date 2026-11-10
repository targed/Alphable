#!/usr/bin/env bash
# scripts/reproduce_benchmarks.sh - Reproduce Alphable V4 Paper Benchmarks
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_EXEC="${REPO_ROOT}/venv/bin/python"

if [ ! -f "${PYTHON_EXEC}" ]; then
    PYTHON_EXEC="python3"
fi

show_help() {
    cat << EOF
Alphable V4 Benchmark Reproduction Suite

Usage:
  ./scripts/reproduce_benchmarks.sh [OPTION]

Options:
  --verify, -v        Verify published statistical claims using the 10,000-game dataset (default, instant)
  --smoke-test, -s    Run a 4-game (2-pair) duplicate match to verify live engine execution (~1 minute)
  --run-tournament N  Run a fresh duplicate tournament with N games (e.g. 100 or 500)
  --help, -h          Show this help message

Examples:
  ./scripts/reproduce_benchmarks.sh                  # Instantly verifies Tables 1 & 2 in the paper
  ./scripts/reproduce_benchmarks.sh --smoke-test     # Runs live smoke test
  ./scripts/reproduce_benchmarks.sh --run-tournament 20 # Runs 20 games (10 duplicate pairs)
EOF
}

MODE="${1:---verify}"

case "${MODE}" in
    --verify|-v)
        "${PYTHON_EXEC}" "${REPO_ROOT}/scripts/verify_historical_telemetry.py"
        ;;
    --smoke-test|-s)
        echo "=== Running Live 4-Game Duplicate Smoke Test ==="
        "${PYTHON_EXEC}" "${REPO_ROOT}/cli.py" tournament --model latest --opponent magpie --games 4 --duplicate
        ;;
    --run-tournament)
        GAMES="${2:-100}"
        echo "=== Running Live Duplicate Tournament (${GAMES} games) ==="
        "${PYTHON_EXEC}" "${REPO_ROOT}/cli.py" tournament --model latest --opponent magpie --games "${GAMES}" --duplicate
        ;;
    --help|-h)
        show_help
        ;;
    *)
        echo "Unknown option: ${MODE}"
        show_help
        exit 1
        ;;
esac
