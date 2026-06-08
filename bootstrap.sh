#!/usr/bin/env bash
# BuilderShip one-shot setup — memory + full sponsor stack
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

export HARBOR_DEMO=1
pytest -q
python examples/demo_compare.py
supercompress doctor --demo
python examples/buildership_loop/run.py

echo ""
echo "✓ BuilderShip stack ready (demo mode)"
echo "  supercompress loop          # full sponsor flow"
echo "  supercompress setup           # add live API keys"
echo "  supercompress loop --live     # real Tavily + Composio + Nebius"
