#!/usr/bin/env bash
# Create + deploy supercompress-api on Render (one-time). Requires RENDER_API_KEY.
set -euo pipefail

if [[ -z "${RENDER_API_KEY:-}" ]]; then
  echo "Export RENDER_API_KEY from https://dashboard.render.com/u/settings#api-keys"
  exit 1
fi

API="https://api.render.com/v1"
OWNER_ID="${RENDER_OWNER_ID:-}"

if [[ -z "$OWNER_ID" ]]; then
  echo "Fetching Render owner id…"
  OWNER_ID=$(curl -fsS "$API/owners" -H "Authorization: Bearer $RENDER_API_KEY" | python3 -c "
import json,sys
owners=json.load(sys.stdin)
print(owners[0]['owner']['id'] if owners else '')
")
fi

if [[ -z "$OWNER_ID" ]]; then
  echo "Could not resolve owner id. Set RENDER_OWNER_ID manually."
  exit 1
fi

echo "Owner: $OWNER_ID"
echo "Syncing Blueprint from render.yaml (recommended) or create service via dashboard:"
echo "  https://dashboard.render.com/select-repo?type=blueprint"
echo ""
echo "After the web service exists, set env vars in Render dashboard:"
echo "  NEBIUS_API_KEY, COMPOSIO_API_KEY, TAVILY_API_KEY"
echo "  FIREBASE_* (for dashboard auth)"
echo "  HARBOR_DEMO=0"
echo ""
echo "Health check: curl https://supercompress-api.onrender.com/v1/health"
