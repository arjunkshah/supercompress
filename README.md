# SuperCompress

**Agent memory layer** — compress Tavily + Composio context before every Nebius inference call.

Agent loops break at turn 4 when tool outputs inflate KV cache. SuperCompress keeps the tokens that matter.

📦 **Repo:** [github.com/arjunkshah/supercompress](https://github.com/arjunkshah/supercompress)  
🎬 **Demo:** `python examples/demo_compare.py`  
📋 **BuilderShip:** [BUILDERSHIP.md](BUILDERSHIP.md) · [PRODUCT.md](PRODUCT.md)

## Quick start

```bash
./bootstrap.sh
python examples/demo_compare.py
```

## Install

```bash
pip install git+https://github.com/arjunkshah/supercompress.git
# or local
pip install -e ".[dev]"
```

## Train checkpoint (~30s)

```bash
supercompress-train --fast
# → checkpoints/default.pt
```

## Use

```python
from supercompress import compress_for_turn, compare_policies

blocks = ["## Tavily\n...", "## GitHub\n..."]
compressed, stats = compress_for_turn(blocks, "triage my PRs", budget_ratio=0.35)
print(stats.kv_savings_pct)  # e.g. 65%
```

## Harbor integration

[Harbor](https://github.com/arjunkshah/harbor) consumes SuperCompress in every agent turn:

```
Tavily → Composio → SuperCompress → Nebius
```

See [PRODUCT.md](PRODUCT.md) for the full BuilderShip story.
