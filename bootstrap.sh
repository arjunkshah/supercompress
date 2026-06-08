#!/usr/bin/env bash
# Full setup + verify (CI / judges) — runs ./setup.sh then smoke tests
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

./setup.sh

# shellcheck disable=SC1091
source .venv/bin/activate
export HARBOR_DEMO=1
pytest -q
./bin/supercompress turns
./bin/supercompress doctor --demo
./bin/supercompress loop

echo ""
echo "✓ BuilderShip stack verified (demo mode)"
