# SuperCompress × Harbor — Product Lock

**One sentence:** SuperCompress is the agent memory layer; Harbor is the runnable demo that proves it across Tavily, Composio, Nebius, and OpenClaw.

**Repo:** https://github.com/arjunkshah/supercompress (memory layer + full sponsor loop)

**Optional:** https://github.com/arjunkshah/harbor (extended workspace demo)

---

## The problem (why we win)

Multi-turn agent loops gather context from Tavily + Composio every turn. By turn 4, KV cache explodes — latency spikes, cost spikes, the model forgets. **Nobody ships a learned eviction policy between gather and inference.** We do.

| Turn | Without SuperCompress | With SuperCompress |
|------|----------------------|-------------------|
| 1 | 2K tokens | 2K → 700 tokens |
| 3 | 8K tokens | 8K → 2.8K tokens |
| 4+ | OOM / collapse | Stable 35–65% KV savings |

---

## What SuperCompress does (features)

| Feature | Description |
|---------|-------------|
| **compress_for_turn()** | Merge context blocks → learned eviction → trimmed text for LLM |
| **compare_policies()** | FIFO vs SuperCompress side-by-side (doctor + demo) |
| **Learned policy** | ~5K-param network, trains in ~30s (`supercompress-train --fast`) |
| **H2O fallback** | Works without checkpoint file |
| **Budget knob** | `budget_ratio=0.35` default — tune per agent |
| **CompressResult** | `original_tokens`, `kept_tokens`, `kv_savings_pct`, `policy_name` |

**In this repo:** `supercompress/stack/` — Tavily, Composio, Nebius, OpenClaw bridge, agent loop CLI.

---

## What Harbor does (demo surface)

| Feature | User value |
|---------|------------|
| **Agent loop** | Tavily gather → Composio act → SuperCompress → Nebius |
| **Dashboard** | Connect, Board, Build, History |
| **CLI** | `harbor run`, `harbor brief`, `harbor doctor` |
| **OpenClaw bridge** | `POST /openclaw/chat` — runtime hook, not the product |

Harbor **imports** `supercompress` — it does not fork the memory code.

---

## User flow (judge demo script)

### Path A — 60 seconds, no keys

```bash
git clone https://github.com/arjunkshah/supercompress.git && cd supercompress
./bootstrap.sh
supercompress doctor --demo
supercompress loop
```

**Say:** "Turn 4 problem. Watch KV savings in the loop output."

### Path B — Live stack (BuilderShip keys)

```bash
harbor setup                                   # Nebius + Composio + Tavily
harbor connect github --wait
harbor doctor                                  # all green
python examples/openclaw_agent_loop/run.py --live
harbor serve                                   # dashboard
```

**Say:** "Real GitHub via Composio, real search via Tavily, compressed before every Nebius call."

### Path C — OpenClaw user

1. Install OpenClaw locally
2. Point skill at Harbor `openclaw/SKILL.md`
3. Chat in OpenClaw → Harbor runs full loop with SuperCompress

---

## Sponsor map (how each one is used)

```
┌─────────────┐
│   USER      │  harbor run / dashboard / OpenClaw chat
└──────┬──────┘
       ▼
┌─────────────┐
│   TAVILY    │  Gather: live web intel before every turn
└──────┬──────┘
       ▼
┌─────────────┐
│  COMPOSIO   │  Gather + Act: GitHub PRs/issues, Gmail, Slack, etc.
└──────┬──────┘
       ▼
┌─────────────┐
│ SUPERCOMPRESS│  Memory: compress merged context (THIS REPO)
└──────┬──────┘
       ▼
┌─────────────┐
│   NEBIUS    │  Inference: Kimi-K2.5 + tool calling
└──────┬──────┘
       ▼
┌─────────────┐
│  COMPOSIO   │  Act: execute tool calls from model
└─────────────┘
```

| Sponsor | Role in loop | Demo moment |
|---------|--------------|-------------|
| **SuperCompress** | Compress before every Nebius call | `compare_policies()` + turn log KV % |
| **Tavily** | Research / intel blocks in context | Search hits printed in agent loop |
| **Composio** | GitHub gather + tool execution | PR list + `GITHUB_*` actions |
| **Nebius** | Reasoning + tool selection | `harbor doctor` inference check |
| **OpenClaw** | Optional runtime / distribution | SKILL.md + `/openclaw/chat` |

**Pitch line:** "OpenClaw is where agents live. SuperCompress is why they don't forget at turn 4. Harbor is the proof."

---

## How we win BuilderShip

| Rubric axis | Evidence |
|-------------|----------|
| **Working demo** | `examples/openclaw_agent_loop/run.py`, `harbor doctor`, CI |
| **Integration depth** | All 5 sponsors in one loop — SuperCompress is the glue |
| **Usefulness** | Every local agent (OpenClaw, Codex, Claude Code) hits RAM at turn 4 |
| **Code quality** | Typed Python, pytest, separate `supercompress` package |
| **Pitch** | Memory layer, not chatbot — 60s demo script above |

**Differentiator vs other teams:** They wire sponsors in series as integrations. We own the **memory layer between gather and inference** — that's SuperCompress.

---

## API contract (locked)

```python
from supercompress import compress_for_turn, compare_policies, CompressResult

compressed_text, result = compress_for_turn(
    context_blocks: list[str],   # Tavily + Composio markdown blocks
    user_query: str,
    budget_ratio: float = 0.35,
) -> tuple[str, CompressResult]
```

Harbor agent loop calls this **once per inference turn** in `harbor/agent/loop.py`.

---

## File ownership

| Repo | Owns |
|------|------|
| `arjunkshah/supercompress` | `supercompress/`, train script, memory tests, PRODUCT.md |
| `arjunkshah/harbor` | Agent loop, Composio, Tavily, Nebius, dashboard, `examples/openclaw_agent_loop/` |

**Dependency:** `harbor` → `supercompress @ git+https://github.com/arjunkshah/supercompress.git`

---

## Not building (scope lock)

- ❌ Another chat UI clone of OpenClaw
- ❌ Full project management / Linear replacement
- ❌ Generic "any Composio app" marketplace
- ✅ Memory layer + one reproducible agent loop + Harbor as demo harness
