# SuperCompress

**Agent memory layer** + **full BuilderShip sponsor stack** in one repo.

Compress Tavily + Composio context before every Nebius inference call. Agent loops break at turn 4 when tool outputs inflate KV cache — SuperCompress keeps the tokens that matter.

📦 **Repo:** [github.com/arjunkshah/supercompress](https://github.com/arjunkshah/supercompress)  
🎬 **60s demo:** `supercompress loop`  
📋 **BuilderShip:** [BUILDERSHIP.md](BUILDERSHIP.md) · [PRODUCT.md](PRODUCT.md)

## Sponsor flow (implemented)

```
You → Tavily → Composio → SuperCompress → Nebius → Composio → repeat
```

| Sponsor | Command / surface |
|---------|-------------------|
| **Tavily** | Gather in `supercompress loop`, `brief`, `incident` |
| **Composio** | GitHub/Gmail gather + tool execution |
| **SuperCompress** | `compress_for_turn()` every inference turn |
| **Nebius** | Token Factory inference + tool calling |
| **OpenClaw** | `openclaw/SKILL.md` + `POST /openclaw/chat` via `supercompress serve` |

## Quick start (no API keys)

```bash
./bootstrap.sh
supercompress doctor --demo
supercompress loop
supercompress demo
```

## Live stack (BuilderShip keys)

```bash
cp .env.example .env
supercompress setup          # Nebius + Composio + Tavily
supercompress connect github gmail --wait
supercompress doctor
supercompress loop --live
supercompress serve          # OpenClaw webhook :8787
```

## Install

```bash
pip install git+https://github.com/arjunkshah/supercompress.git
# or local
pip install -e ".[dev]"
supercompress-train --fast
```

## Python API

```python
from supercompress import compress_for_turn, compare_policies

blocks = ["## Tavily\n...", "## GitHub\n..."]
compressed, stats = compress_for_turn(blocks, "triage my PRs", budget_ratio=0.35)
print(stats.kv_savings_pct)  # e.g. 65%
```

## CLI

| Command | What |
|---------|------|
| `supercompress loop` | Full sponsor demo loop |
| `supercompress doctor` | Health check all integrations |
| `supercompress brief` | Morning brief workflow |
| `supercompress incident "…"` | Incident commander |
| `supercompress setup` | Interactive key setup |
| `supercompress connect github` | Composio OAuth |
| `supercompress serve` | API + OpenClaw bridge |
| `supercompress-train --fast` | Train memory checkpoint |

## Harbor

[Harbor](https://github.com/arjunkshah/harbor) is an optional extended demo workspace. This repo is the **submission product** — memory layer + sponsor loop.
