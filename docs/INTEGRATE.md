# Integrate SuperCompress — Timmy's productivity app

**Timmy** builds a productivity app with an AI chat. He uses Composio so users can email him to add/edit reminders. He was using OpenAI directly.

**SuperCompress replaces the OpenAI call** — every turn still runs **Tavily + Composio + SuperCompress + Nebius**. Timmy passes his app state; we handle the rest.

---

## What changes for Timmy

| Before | After |
|--------|-------|
| Gather tasks + Composio emails | Same — his code |
| Send everything to **OpenAI** | Send query + blocks to **SuperCompress** |
| OpenAI returns answer | **Nebius** returns `answer` (via our API) |
| Composio sends emails | Same — or Nebius can trigger Composio tools |

Timmy does **not** need Tavily or Nebius API keys. We host those. He **does** connect Composio in our dashboard (Gmail) so every API call gathers his linked apps.

---

## Setup (5 minutes)

1. **Dashboard** → sign up → create API key (`sc_live_...`)
2. **Integrations** tab → connect **Gmail** (and GitHub/Linear if useful)
3. Replace OpenAI chat call with one HTTP request

---

## Code — one turn in Timmy's backend

```python
import httpx

SC_URL = "https://supercompress-api.onrender.com"  # or /v1 via Vercel proxy
SC_KEY = "sc_live_..."

async def handle_user_chat(user_id: str, message: str):
    tasks = await db.get_tasks(user_id)
    reminders = await db.get_reminders(user_id)

    # Your app state — SuperCompress merges this with Tavily + Composio + compress + Nebius
    context_blocks = [
        f"## User tasks\n{format_tasks(tasks)}",
        f"## Reminders\n{format_reminders(reminders)}",
    ]

    r = httpx.post(
        f"{SC_URL}/v1/agent/turn",
        headers={"X-API-Key": SC_KEY},
        json={"query": message, "context_blocks": context_blocks},
        timeout=120,
    )
    data = r.json()

    # Show in your chat UI — from Nebius, not OpenAI
    return {
        "reply": data["answer"],
        "kv_saved": data["memory"]["kv_savings_pct"],
        "phases": data["phases"],  # tavily → composio → compress → nebius
    }
```

---

## What runs on **every** call (non-optional)

| Sponsor | What happens |
|---------|----------------|
| **Tavily** | Live web research for the user's query |
| **Composio** | Snapshots from **Timmy's** connected Gmail/GitHub/etc. + tool execution |
| **SuperCompress** | Compresses Tavily + Composio + Timmy's blocks (~65% KV savings) |
| **Nebius** | LLM answer on compressed context |

`stack` in the response is always `{ tavily, composio, supercompress, nebius: true }`.

---

## Where Timmy's Composio fits

- **Dashboard connect** — Timmy links Gmail once; our API gathers email state every turn (same inbox he uses for user contact).
- **His existing Composio flows** — can stay for edge cases, or let Nebius call Composio tools via our loop (`actions` in response).
- **His DB** — always passed as `context_blocks`; never skipped.

---

## Mental model

> "I stopped calling OpenAI. I call SuperCompress. My tasks go in `context_blocks`. Tavily, Composio, compression, and Nebius happen automatically."

That's the product — sponsors every time, works for any AI app builder.
