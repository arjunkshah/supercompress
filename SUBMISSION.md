# BuilderShip submission — SuperCompress

## Repo

https://github.com/arjunkshah/supercompress

## One-liner

SuperCompress is the agent memory layer with a full BuilderShip sponsor loop — Tavily gather, Composio act, learned KV eviction, Nebius inference.

## What it does

Multi-turn agents accumulate tool output every turn. By turn 4, context explodes. SuperCompress trims context with a learned policy (~65% KV savings) **before every Nebius call**, in a reproducible sponsor stack.

## Demo commands (judges)

```bash
git clone https://github.com/arjunkshah/supercompress.git
cd supercompress
./bootstrap.sh
supercompress loop
```

Live (with BuilderShip keys):

```bash
supercompress setup
supercompress connect github gmail --wait
supercompress loop --live
```

## Stack — all sponsors wired

| Sponsor | Evidence |
|---------|----------|
| **Tavily** | `supercompress loop` step 1 — search + synthesize |
| **Composio** | GitHub gather + tool execution in agent loop |
| **SuperCompress** | `compress_for_turn()` + `compare_policies()` |
| **Nebius** | Token Factory chat + tool calling |
| **OpenClaw** | `openclaw/SKILL.md` + `/openclaw/chat` |

## Video script (60s)

1. Problem: "Turn 4 — your agent forgets because KV cache exploded."
2. `supercompress loop` — show Tavily → Composio → compression → Nebius.
3. Point at KV savings % in output.
4. Optional: `supercompress serve` + OpenClaw skill.
5. "pip install supercompress — drop into any agent loop."

## Links

- Product spec: [PRODUCT.md](PRODUCT.md)
- BuilderShip checklist: [BUILDERSHIP.md](BUILDERSHIP.md)
- https://ship.builders
