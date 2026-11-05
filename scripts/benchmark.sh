#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p benchmarks/results
saqr benchmark --frames 60 --width 640 --height 480 --out benchmarks/results/bench-cpu-640.json
echo "Saved benchmarks/results/bench-cpu-640.json"
