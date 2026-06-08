# SuperCompress API

**Official API:** https://supercompress-api.onrender.com  
**Dashboard (API keys):** https://buildersshipbycursor.vercel.app/dashboard.html

## Primary: `POST /v1/agent/turn`

Send a query. We run **Tavily → Composio → SuperCompress → Nebius** with hosted keys.

```bash
curl -X POST https://supercompress-api.onrender.com/v1/agent/turn \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sc_live_YOUR_KEY" \
  -d '{"query": "What PRs need review?"}'
```

Response: `answer`, `memory` (KV savings), `phases`, `actions`.

---

## Advanced: compress-only endpoints

If you gather context yourself:

## 1. Python package (in-process, fastest)

Best for: Python agents, LangChain, OpenClaw backends, same machine as your loop.

```bash
pip install git+https://github.com/arjunkshah/supercompress.git
supercompress-train --fast
```

```python
from supercompress import compress_for_turn

blocks = [
    tavily_client.search(...).to_markdown(),
    composio_client.github_snapshot().to_markdown(),
]
compressed, stats = compress_for_turn(blocks, user_query, budget_ratio=0.35)

# Send `compressed` to your LLM instead of the full pile
response = nebius.chat([
    {"role": "user", "content": f"## Context\n{compressed}\n\n## Task\n{user_query}"}
])
print(stats.kv_savings_pct)  # e.g. 65.0
```

---

## 2. HTTP API (any language)

Best for: Node, Go, Rust, mobile, microservices, team-shared compression service.

**Start the server:**

```bash
./setup.sh
./bin/supercompress serve
# → http://127.0.0.1:8787
# Interactive docs → http://127.0.0.1:8787/docs
```

### `POST /v1/compress/blocks` (recommended)

```bash
curl -s http://127.0.0.1:8787/v1/compress/blocks \
  -H "Content-Type: application/json" \
  -d '{
    "context_blocks": [
      "## Tavily\nMarket news about AI agents...",
      "## GitHub\nPR #42 needs review"
    ],
    "query": "What should I ship today?",
    "budget_ratio": 0.35
  }'
```

**Response:**

```json
{
  "compressed_text": "## Tavily\n...\n## GitHub\nPR #42...",
  "stats": {
    "original_tokens": 164,
    "kept_tokens": 57,
    "kv_savings_pct": 65.2,
    "policy_name": "SuperCompress",
    "budget_ratio": 0.35,
    "fifo_kept_tokens": 57
  }
}
```

### Other endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/v1/health` | Service status |
| `POST` | `/v1/compress` | Single text blob (splits on `---`) |
| `POST` | `/v1/compare` | FIFO vs SuperCompress side-by-side |
| `GET` | `/v1/turns/demo` | Turn 1–4 demo data |
| `GET` | `/docs` | Swagger UI |

Legacy alias: `/api/*` mirrors `/v1/*`.

---

## 3. Python HTTP client

Best for: Python projects that want a separate compression service.

```python
from supercompress.http_client import SuperCompressClient

with SuperCompressClient("http://127.0.0.1:8787") as sc:
    result = sc.compress_blocks(
        ["## GitHub\nPR #42", "## Gmail\nurgent email"],
        "triage my morning",
    )
    print(result.compressed_text)
    print(f"{result.stats.kv_savings_pct}% saved")
```

---

## Where to call it in your agent loop

```
every turn:
  1. gather from Tavily, Composio, etc. → context_blocks[]
  2. compressed, stats = compress_for_turn(blocks, user_query)   # ← HERE
  3. llm.chat(compressed + user_query)
  4. execute tools from LLM
  5. repeat
```

---

## Deploy for your team

Self-host on any machine with Python 3.10+:

```bash
pip install -e .
supercompress-train --fast
supercompress serve --host 0.0.0.0 --port 8787
```

Point all your agents at `http://your-server:8787/v1/compress/blocks`.

CORS is enabled — browser and server clients both work.

---

## JavaScript example

```javascript
const res = await fetch("http://127.0.0.1:8787/v1/compress/blocks", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    context_blocks: [tavilyBlock, githubBlock],
    query: "What should I ship?",
    budget_ratio: 0.35,
  }),
});
const { compressed_text, stats } = await res.json();
// send compressed_text to your LLM
```
