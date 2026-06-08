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
# Public Firebase web config (same values baked into Vercel config.js)
os.environ.setdefault("FIREBASE_PROJECT_ID", "supercompress")
os.environ.setdefault("FIREBASE_API_KEY", "AIzaSyAJb0YYhZzA47HLWAqxCM9wmb9CxEJDIEw")
os.environ.setdefault("FIREBASE_AUTH_DOMAIN", "supercompress.firebaseapp.com")
os.environ.setdefault("FIREBASE_APP_ID", "1:860458844973:web:a79ebe5706444cb62a09a4")
os.environ.setdefault("FIREBASE_MESSAGING_SENDER_ID", "860458844973")
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
