#!/usr/bin/env python3
"""60-second demo: FIFO vs SuperCompress on agent-style context."""

from __future__ import annotations

from supercompress import compare_policies, compress_for_turn

TAVILY = """## Tavily research: OpenClaw agent adoption
**Synthesis:** Composio shipped an OpenClaw plugin. Nebius Token Factory added Kimi K2.5.
- Composio OpenClaw MCP router (score 0.94)
- Nebius serverless deploy docs (score 0.91)
"""

GITHUB = """## GitHub (Composio)
### PRs needing your review
- #42 fix/auth-timeout — 3 files, CI green, waiting 18h
- #39 feat/composio-triggers — draft

### Open issues
- #38 memory blow-up on turn 4 — P1
"""

GMAIL = """## Gmail (Composio)
- From: sponsor@builders — "Demo video due June 12"
- From: teammate — "Can you review PR #42?"
"""


def main() -> None:
    blocks = [TAVILY, GITHUB, GMAIL]
    query = "What should I do first this morning?"

    print("SuperCompress — turn 4 memory demo\n")
    print(f"Query: {query}\n")

    merged = "\n\n---\n\n".join(blocks)
    cmp = compare_policies(merged, query, budget_ratio=0.35)

    for name, result in cmp.items():
        print(f"── {name} ({result.policy_name})")
        print(f"   tokens: {result.original_tokens} → {result.kept_tokens}")
        print(f"   KV savings: {result.kv_savings_pct:.1f}%")
        print()

    compressed, stats = compress_for_turn(blocks, query)
    print("── compress_for_turn() (Harbor agent loop API)")
    print(f"   policy: {stats.policy_name}")
    print(f"   KV savings: {stats.kv_savings_pct:.1f}%")
    print(f"   preview: {compressed[:200].replace(chr(10), ' ')}…")


if __name__ == "__main__":
    main()
