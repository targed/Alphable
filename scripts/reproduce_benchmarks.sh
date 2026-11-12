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
Alphable V4 Benchmark & Tournament Reproduction Suite

Usage:
  ./scripts/reproduce_benchmarks.sh [OPTION] [ARGUMENTS...]

Options:
  --verify, -v                 Verify published statistical claims using the 10,000-game dataset (default, instant)
  --hybrid-vs-tuned [GAMES]    Run duplicate tournament: Hybrid PIMC vs Maximally Tuned MAGPIE (default: 40 games / 20 pairs)
  --hybrid-smoke               Run quick 4-game smoke test: Hybrid PIMC vs Maximally Tuned MAGPIE (~45 seconds)
  --smoke-test, -s             Run 4-game duplicate smoke test: V4 Champion vs 1-ply Base MAGPIE (~1 minute)
  --run-tournament [G] [M] [O] Run flexible duplicate tournament:
                               [G] Games count (default: 40)
                               [M] Player 1 model preset (default: hybrid-pimc)
                               [O] Player 2 opponent preset (default: magpie-tuned)
  --help, -h                   Show this help message

Model Presets:
  hybrid-pimc                  SOTA Hybrid Engine (Native C PIMC rollouts + Cross-Attention Value Re-Ranking)
  latest / champion            Alphable V4 Champion 2-Ply BAMS
  v4-pat                       V4 2-Ply BAMS with PAT candidate generator
  5-frontiers                  V4 5-Frontiers integrated search
  magpie-tuned                 Maximally Tuned Base MAGPIE (-pat CSW24, C PIMC, exact endgame)
  magpie                       Default 1-ply Static KLV Base MAGPIE

Examples:
  ./scripts/reproduce_benchmarks.sh                      # Instantly verifies Tables 1 & 2 in the paper
  ./scripts/reproduce_benchmarks.sh --hybrid-smoke       # Runs quick 4-game smoke test of Hybrid PIMC vs Tuned MAGPIE
  ./scripts/reproduce_benchmarks.sh --hybrid-vs-tuned 40 # Runs 40-game duplicate benchmark of Hybrid PIMC vs Tuned MAGPIE
  ./scripts/reproduce_benchmarks.sh --run-tournament 100 hybrid-pimc magpie-tuned
EOF
}

MODE="${1:---verify}"

case "${MODE}" in
    --verify|-v)
        "${PYTHON_EXEC}" "${REPO_ROOT}/scripts/verify_historical_telemetry.py"
        ;;
    --hybrid-smoke)
        echo "=== Running Live 4-Game Duplicate Smoke Test (Hybrid PIMC vs Tuned MAGPIE) ==="
        "${PYTHON_EXEC}" "${REPO_ROOT}/cli.py" tournament --model hybrid-pimc --opponent magpie-tuned --games 4 --duplicate
        ;;
    --hybrid-vs-tuned)
        GAMES="${2:-40}"
        echo "=== Running Hybrid PIMC vs Maximally Tuned MAGPIE Duplicate Tournament (${GAMES} games) ==="
        "${PYTHON_EXEC}" "${REPO_ROOT}/cli.py" tournament --model hybrid-pimc --opponent magpie-tuned --games "${GAMES}" --duplicate
        ;;
    --smoke-test|-s)
        echo "=== Running Live 4-Game Duplicate Smoke Test (V4 Champion vs Base MAGPIE) ==="
        "${PYTHON_EXEC}" "${REPO_ROOT}/cli.py" tournament --model latest --opponent magpie --games 4 --duplicate
        ;;
    --run-tournament)
        GAMES="${2:-40}"
        MODEL="${3:-hybrid-pimc}"
        OPPONENT="${4:-magpie-tuned}"
        echo "=== Running Live Duplicate Tournament: ${MODEL} vs ${OPPONENT} (${GAMES} games) ==="
        "${PYTHON_EXEC}" "${REPO_ROOT}/cli.py" tournament --model "${MODEL}" --opponent "${OPPONENT}" --games "${GAMES}" --duplicate
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
