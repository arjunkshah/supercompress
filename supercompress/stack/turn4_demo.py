"""Turn 4 demo — show context growth vs SuperCompress holding the line."""

from __future__ import annotations

from supercompress import compare_policies, compress_for_turn

TURN_BLOCKS = [
    [
        "## Tavily\nOpenClaw adoption rising. Composio ships MCP router.",
        "## GitHub\nPR #42 auth-timeout — review requested.",
    ],
    [
        "## Tavily\nOpenClaw adoption rising. Composio ships MCP router.",
        "## GitHub\nPR #42 auth-timeout — review requested.",
        "## Tool result\nFetched 12 open PRs across 3 repos.",
        "## Gmail\n2 unread from sponsor@builders.",
    ],
    [
        "## Tavily\nOpenClaw adoption rising. Composio ships MCP router.",
        "## GitHub\nPR #42 auth-timeout — review requested.",
        "## Tool result\nFetched 12 open PRs across 3 repos.",
        "## Gmail\n2 unread from sponsor@builders.",
        "## Tool result\nPosted Slack digest to #builders.",
        "## Tavily\nLatest Nebius Kimi K2.5 serverless docs.",
    ],
    [
        "## Tavily\nOpenClaw adoption rising. Composio ships MCP router.",
        "## GitHub\nPR #42 auth-timeout — review requested.",
        "## Tool result\nFetched 12 open PRs across 3 repos.",
        "## Gmail\n2 unread from sponsor@builders.",
        "## Tool result\nPosted Slack digest to #builders.",
        "## Tavily\nLatest Nebius Kimi K2.5 serverless docs.",
        "## Tool result\nCreated Linear ENG-231 follow-up.",
        "## GitHub\n3 new commits on main since last turn.",
        "## Tavily\nCompetitor launch: new agent memory product.",
    ],
]

QUERY = "What should I ship today?"


def run_turn4_demo() -> int:
    print("\n" + "=" * 60)
    print("  Turn 4 — why agents forget (and how SuperCompress fixes it)")
    print("=" * 60 + "\n")

    for turn, blocks in enumerate(TURN_BLOCKS, start=1):
        merged = "\n\n---\n\n".join(blocks)
        raw_tokens = len(merged.split())  # rough proxy for judges
        _, sc = compress_for_turn(blocks, QUERY)
        cmp = compare_policies(merged, QUERY)
        fifo = cmp["FIFO"]

        bar_raw = "█" * min(40, raw_tokens // 8)
        bar_sc = "█" * min(40, sc.kept_tokens // 4)

        print(f"Turn {turn}  ·  {len(blocks)} context blocks  ·  ~{raw_tokens} words raw")
        print(f"  Without memory layer (FIFO):     {fifo.kept_tokens:4d} tokens kept")
        print(f"  With SuperCompress:              {sc.kept_tokens:4d} tokens  ({sc.kv_savings_pct:.0f}% KV saved)")
        print(f"  Raw growth:  [{bar_raw:<40}]")
        print(f"  Compressed:  [{bar_sc:<40}]")
        print()

    print("=" * 60)
    print("  Agents gather more every turn. SuperCompress trims before inference.")
    print("  pip install supercompress  ·  github.com/arjunkshah/supercompress")
    print("=" * 60 + "\n")
    return 0
