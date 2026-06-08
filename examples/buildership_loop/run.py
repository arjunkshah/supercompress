#!/usr/bin/env python3
"""
BuilderShip sponsor loop — Tavily → Composio → SuperCompress → Nebius

  HARBOR_DEMO=1 python examples/buildership_loop/run.py
  python examples/buildership_loop/run.py --live   # after supercompress setup
"""

from __future__ import annotations

import argparse

from supercompress.stack.demo_loop import run_loop


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task", default="Triage my open GitHub PRs and suggest what to ship")
    p.add_argument("--live", action="store_true")
    args = p.parse_args()
    raise SystemExit(run_loop(task=args.task, live=args.live))


if __name__ == "__main__":
    main()
