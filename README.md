# SuperCompress

**Agent memory API** — send a query, get an answer. We run Tavily, Composio, SuperCompress, and Nebius for you.

🌐 **Site:** [buildersshipbycursor.vercel.app](https://buildersshipbycursor.vercel.app)  
🔑 **Dashboard:** [Get API key](https://buildersshipbycursor.vercel.app/dashboard.html)  
🔌 **API:** [supercompress-api.onrender.com/docs](https://supercompress-api.onrender.com/docs)

## The product

**Replace your OpenAI call.** Every request runs **all sponsors** — no exceptions.

```bash
curl -X POST https://supercompress-api.onrender.com/v1/agent/turn \
  -H "X-API-Key: sc_live_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What should I focus on?",
    "context_blocks": ["## Tasks\n- Ship onboarding", "## Reminders\n- Dentist Tue 3pm"]
  }'
```

| Sponsor | Every call |
|---------|------------|
| **Tavily** | Web research for the query |
| **Composio** | Your connected apps (connect Gmail/GitHub in dashboard) |
| **Your app** | `context_blocks` — tasks, reminders, user state |
| **SuperCompress** | Compress everything (~65% KV savings) |
| **Nebius** | `answer` for your chat UI |

**Integrate like Timmy:** [docs/INTEGRATE.md](docs/INTEGRATE.md)

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
