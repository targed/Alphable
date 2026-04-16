#!/usr/bin/env bash
set -euo pipefail

RL_DIR="data/rl"
OUT_FILE="$RL_DIR/rl_vs_greedy_combined.jsonl"

shopt -s nullglob
files=("$RL_DIR"/rl_vs_greedy[0-9]*.jsonl)

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No files matched: $RL_DIR/rl_vs_greedy[0-9]*.jsonl"
  exit 1
fi

IFS=$'\n' files=($(printf '%s\n' "${files[@]}" | sort -V))
unset IFS

: > "$OUT_FILE"
for f in "${files[@]}"; do
  cat "$f" >> "$OUT_FILE"
done

echo "Combined ${#files[@]} files into $OUT_FILE"
wc -l "$OUT_FILE"
