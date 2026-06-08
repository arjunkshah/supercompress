#!/usr/bin/env bash
# One-shot setup for SuperCompress (BuilderShip submission)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -U pip -q
pip install -e ".[dev]" -q

if [[ ! -f checkpoints/default.pt ]]; then
  supercompress-train --fast
fi

pytest -q
python examples/demo_compare.py

echo ""
echo "Ready. Next:"
echo "  python examples/demo_compare.py   # 60s judge demo"
echo "  See PRODUCT.md + BUILDERSHIP.md"
