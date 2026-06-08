#!/usr/bin/env bash
# Run live API locally and expose via ngrok (until Render Blueprint is deployed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

# Load .env without exporting comments
python3 - <<'PY'
from dotenv import load_dotenv
import os, subprocess, sys
load_dotenv(".env")
load_dotenv(".env.vercel", override=True)
os.environ["HARBOR_DEMO"] = "0"
# Start uvicorn in background
subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "supercompress.stack.server_api:app", "--host", "127.0.0.1", "--port", "8799"],
    cwd=".",
)
PY

sleep 2
curl -fsS http://127.0.0.1:8799/v1/health >/dev/null && echo "API ok on :8799"

echo "Starting ngrok… Update vercel.json rewrites to the URL below, then: vercel --prod"
exec ngrok http 8799
