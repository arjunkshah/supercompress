#!/usr/bin/env bash
# One-time setup — creates venv, installs CLI, trains checkpoint
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "▸ SuperCompress setup"
echo ""

if [[ -f .env ]]; then
  echo "▸ Found .env (live keys)"
elif [[ -f "../harbor/harbor collective/.env" ]]; then
  echo "▸ Copying keys from Harbor .env…"
  cp "../harbor/harbor collective/.env" .env
  sed -i '' 's|GITHUB_REPO=.*github.com.*/\(.*\)\.git|GITHUB_REPO=\1|' .env 2>/dev/null || true
elif [[ -f "$HOME/Downloads/harbor/harbor collective/.env" ]]; then
  cp "$HOME/Downloads/harbor/harbor collective/.env" .env
  sed -i '' 's|GITHUB_REPO=.*github.com.*/\(.*\)\.git|GITHUB_REPO=\1|' .env 2>/dev/null || true
fi
echo ""

if ! command -v python3 &>/dev/null; then
  echo "✗ python3 not found. Install Python 3.10+ first."
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "▸ Creating virtualenv (.venv)…"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "▸ Installing package + dependencies…"
pip install -U pip -q
pip install -e ".[dev]" -q

if [[ ! -f checkpoints/default.pt ]]; then
  echo "▸ Training memory checkpoint (~30s)…"
  supercompress-train --fast
else
  echo "▸ Checkpoint OK (checkpoints/default.pt)"
fi

chmod +x bin/supercompress bootstrap.sh examples/buildership_loop/run.py 2>/dev/null || true

echo ""
echo "✓ Setup complete"
echo ""
echo "Run commands from this folder:"
echo "  ./bin/supercompress turns     # turn 4 problem (best for Twitter)"
echo "  ./bin/supercompress loop      # full sponsor stack demo"
echo "  ./bin/supercompress doctor    # health check"
echo "  ./bin/supercompress serve     # landing page :8787"
echo ""
echo "Or activate the venv once per terminal:"
echo "  source .venv/bin/activate"
echo "  supercompress loop"
echo ""
echo "Live stack (after you have keys):"
echo "  ./bin/supercompress setup     # interactive .env + OAuth"
echo "  ./bin/supercompress loop --live"
