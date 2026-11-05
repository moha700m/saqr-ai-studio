#!/usr/bin/env bash
# One-command developer setup on Linux/macOS.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e "engine[dev]"

if command -v npm >/dev/null; then
  (cd web && npm ci && npm run build)
fi

echo
saqr doctor
echo
echo "Next: saqr models download yunet-2023mar"
echo "      saqr serve --pair"
