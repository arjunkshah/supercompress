# SuperCompress

**Your agent forgets at turn 4. We fix that.**

The memory layer for AI agents — compress Tavily + Composio context **before every inference call**. ~65% KV savings. Agents keep going.

🌐 **Site:** [arjunkshah.github.io/supercompress](https://arjunkshah.github.io/supercompress)  
📦 **Repo:** [github.com/arjunkshah/supercompress](https://github.com/arjunkshah/supercompress)  
🐦 **Launch copy:** [LAUNCH.md](LAUNCH.md)

## 60 seconds

```bash
git clone https://github.com/arjunkshah/supercompress.git
cd supercompress
./setup.sh
./bin/supercompress turns    # show the turn 4 problem
./bin/supercompress loop     # full Tavily → Composio → Nebius stack
```

## What it is

| Layer | Role |
|-------|------|
| **Tavily** | Pours in live web research (creates bloat) |
| **Composio** | App state + tool actions (multi-turn trap) |
| **SuperCompress** | **Trims context before the model reads it** |
| **Nebius** | Inference on compressed input — faster, cheaper |
| **OpenClaw** | Runtime hook for long agent sessions |

## Install

```bash
pip install git+https://github.com/arjunkshah/supercompress.git
supercompress-train --fast
```

```python
from supercompress import compress_for_turn

compressed, stats = compress_for_turn(
    ["## Tavily\n...", "## GitHub\n..."],
    "what should I ship today?",
)
print(f"{stats.kv_savings_pct:.0f}% KV saved")
```

## CLI

| Command | What |
|---------|------|
| `./bin/supercompress turns` | Turn 4 visualization (Twitter/video) |
| `./bin/supercompress loop` | Full sponsor stack |
| `./bin/supercompress doctor` | Health check |
| `./bin/supercompress setup` | API keys + OAuth |
| `./bin/supercompress serve` | Site + API on :8787 |

## Live stack

```bash
cp .env.example .env   # or ./bin/supercompress setup
./bin/supercompress connect github gmail --wait
./bin/supercompress loop --live
```

## BuilderShip

[BUILDERSHIP.md](BUILDERSHIP.md) · [PRODUCT.md](PRODUCT.md) · [SUBMISSION.md](SUBMISSION.md)

MIT · Built for agents that actually run.
