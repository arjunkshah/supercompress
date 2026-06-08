# BuilderShip submission — SuperCompress

## Repo

https://github.com/arjunkshah/supercompress

## One-liner

SuperCompress is the agent memory layer — learned KV eviction between Tavily/Composio gather and Nebius inference.

## What it does

Multi-turn agents accumulate tool output every turn. By turn 4, context explodes — latency, cost, and forgetting. SuperCompress trims context with a ~5K-param learned policy (~65% KV savings vs FIFO) before every LLM call.

## Demo commands

```bash
./bootstrap.sh
python examples/demo_compare.py
```

Full sponsor stack (Harbor):

```bash
git clone https://github.com/arjunkshah/harbor.git
HARBOR_DEMO=1 python examples/openclaw_agent_loop/run.py
```

## Stack

- **SuperCompress** — memory (this repo)
- **Harbor** — demo harness
- **Tavily** — search
- **Composio** — GitHub, Gmail, tools
- **Nebius** — Kimi K2.5 inference
- **OpenClaw** — agent runtime hook

## Video script (60s)

1. Problem: "Turn 4 — your agent forgets because KV cache exploded."
2. Run `python examples/demo_compare.py` — show FIFO vs SuperCompress token counts.
3. "This runs inside Harbor on every Nebius call — Tavily + Composio in, compressed out."
4. Optional: `HARBOR_DEMO=1` Harbor agent loop clip.
5. "pip install supercompress — drop into any agent loop."

## Links

- Product spec: [PRODUCT.md](PRODUCT.md)
- Harbor demo: https://github.com/arjunkshah/harbor
- BuilderShip: https://ship.builders
