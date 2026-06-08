# Deploy — website + official public API

SuperCompress ships in two parts:

| Part | Host | URL |
|------|------|-----|
| **Website** (landing, demo, docs) | Vercel | https://buildersshipbycursor.vercel.app |
| **Public API** (compress for any dev) | Render (Docker) | https://supercompress-api.onrender.com |

PyTorch is too heavy for Vercel serverless. The API runs in a Docker container on Render.

---

## Website → Vercel

```bash
npm i -g vercel   # or: npx vercel
vercel --prod
```

`vercel.json` serves `web/` and proxies `/v1/*` to the Render API so browser demos work same-origin.

Optional env in Vercel dashboard:

- `SUPERCOMPRESS_API_URL` — override API base (default: Render URL)

---

## API → Render

1. Push this repo to GitHub.
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect `arjunkshah/supercompress` — Render reads `render.yaml`.
4. Wait ~10 min for Docker build (installs torch + trains checkpoint).
5. Health check: `GET https://supercompress-api.onrender.com/v1/health`

### Self-host API (Railway / Fly / any Docker host)

```bash
docker build -f deploy/Dockerfile -t supercompress-api .
docker run -p 8000:8000 -e HARBOR_DEMO=1 supercompress-api
```

---

## For developers building AI apps

**One HTTP call** — any language:

```bash
POST https://supercompress-api.onrender.com/v1/compress/blocks
Content-Type: application/json

{
  "context_blocks": ["tavily markdown", "github markdown", "gmail markdown"],
  "query": "What should the agent do next?",
  "budget_ratio": 0.35
}
```

Returns `{ "compressed_text": "...", "stats": { "kv_savings_pct": 65.0, ... } }`.

Python client:

```python
from supercompress.http_client import SuperCompressClient

with SuperCompressClient() as client:  # defaults to official API
    result = client.compress_blocks(blocks, query)
    send_to_llm(result.compressed_text)
```

---

## Local dev (unchanged)

```bash
./setup.sh
./bin/supercompress serve   # site + API on :8787
```
