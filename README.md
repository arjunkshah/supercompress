# SuperCompress

**Agent memory API** — send a query, get an answer. We run Tavily, Composio, SuperCompress, and Nebius for you.

🌐 **Site:** [buildersshipbycursor.vercel.app](https://buildersshipbycursor.vercel.app)  
🔑 **Dashboard:** [Get API key](https://buildersshipbycursor.vercel.app/dashboard.html)  
🔌 **API:** [supercompress-api.onrender.com/docs](https://supercompress-api.onrender.com/docs)

## The product

```bash
curl -X POST https://supercompress-api.onrender.com/v1/agent/turn \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sc_live_YOUR_KEY" \
  -d '{"query": "What PRs need review and what should I ship?"}'
```

**One call runs:**

| Step | Sponsor | What it does |
|------|---------|--------------|
| 1 | **Tavily** | Live web research for your query |
| 2 | **Composio** | GitHub, Gmail, Linear snapshots (+ tool execution) |
| 3 | **SuperCompress** | Memory compression (~65% KV savings) |
| 4 | **Nebius** | LLM answer on trimmed context |

You get `answer`, `memory` stats, `phases`, and `actions`. No Tavily/Composio/Nebius keys on your side — we host the stack.

## Python client

```python
from supercompress.http_client import SuperCompressClient

with SuperCompressClient(api_key="sc_live_...") as client:
    result = client.agent_turn("What should I ship today?")
    print(result["answer"])
    print(result["memory"]["kv_savings_pct"], "% saved")
```

## Self-host

```bash
./setup.sh
cp .env.example .env   # add NEBIUS, COMPOSIO, TAVILY keys
./bin/supercompress serve   # dashboard + API on :8787
```

## Advanced

`POST /v1/compress/blocks` — compress context you already gathered. Most apps use `/v1/agent/turn`.

Docs: [docs/API.md](docs/API.md) · [DEPLOY.md](DEPLOY.md)

MIT
