#!/usr/bin/env python3
"""Example: call SuperCompress API from another project."""

from supercompress.http_client import SuperCompressClient

BLOCKS = [
    "## Tavily\nComposio shipped OpenClaw plugin.",
    "## GitHub\n- #42 auth-timeout — review requested",
]

if __name__ == "__main__":
    with SuperCompressClient("http://127.0.0.1:8787") as client:
        print("Health:", client.health())
        result = client.compress_blocks(BLOCKS, "What PR should I review first?")
        print(f"\nKV savings: {result.stats.kv_savings_pct}%")
        print(f"Policy: {result.stats.policy_name}")
        print("\nCompressed context:\n", result.compressed_text[:500])
