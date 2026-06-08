#!/usr/bin/env python3
"""Export static demo data for GitHub Pages (no backend required)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "data" / "demo.json"

from supercompress import compare_policies, compress_for_turn
from supercompress.stack.turn4_demo import QUERY, TURN_BLOCKS

SAMPLE_CONTEXT = """## Tavily research
**Synthesis:** Composio shipped OpenClaw plugin. Nebius added Kimi K2.5.

### [1] Composio OpenClaw MCP router
URL: https://composio.dev/toolkits/composio/framework/openclaw
Connects agents to 250+ apps via MCP.

---
## GitHub (Composio)
### PRs needing review
- #42 fix/auth-timeout — CI green, waiting 18h
- #39 feat/composio-triggers — draft

---
## Gmail
- sponsor@builders — Demo video due June 12
- teammate — Can you review PR #42?"""


def main() -> None:
    turns = []
    for i, blocks in enumerate(TURN_BLOCKS, start=1):
        merged = "\n\n---\n\n".join(blocks)
        _, sc = compress_for_turn(blocks, QUERY)
        cmp = compare_policies(merged, QUERY)
        fifo = cmp["FIFO"]
        turns.append(
            {
                "turn": i,
                "blocks": len(blocks),
                "words": len(merged.split()),
                "fifo_tokens": fifo.kept_tokens,
                "sc_tokens": sc.kept_tokens,
                "kv_savings_pct": round(sc.kv_savings_pct, 1),
                "original_tokens": sc.original_tokens,
            }
        )

    blocks = [b.strip() for b in SAMPLE_CONTEXT.split("---") if b.strip()]
    compressed, result = compress_for_turn(blocks, "What should I ship today?")
    cmp = compare_policies("\n\n---\n\n".join(blocks), "What should I ship today?")

    payload = {
        "turns": turns,
        "query": QUERY,
        "sample": {
            "query": "What should I ship today?",
            "original_tokens": result.original_tokens,
            "kept_tokens": result.kept_tokens,
            "kv_savings_pct": round(result.kv_savings_pct, 1),
            "fifo_tokens": cmp["FIFO"].kept_tokens,
            "policy": result.policy_name,
            "compressed_preview": compressed[:1200],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
