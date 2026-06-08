# BuilderShip — SuperCompress submission

**Product:** Agent memory layer between gather (Tavily + Composio) and inference (Nebius).

**Pitch:** OpenClaw is where agents live. SuperCompress is why they don't forget at turn 4. [Harbor](https://github.com/arjunkshah/harbor) is the live proof.

## 60-second demo (no API keys)

```bash
git clone https://github.com/arjunkshah/supercompress.git
cd supercompress
./bootstrap.sh
```

**Say:** "By turn 4, tool outputs blow up KV cache. Watch FIFO vs our learned policy."

## Full stack demo (Harbor)

```bash
git clone https://github.com/arjunkshah/harbor.git && cd harbor
./bootstrap.sh
HARBOR_DEMO=1 python examples/openclaw_agent_loop/run.py
```

## Sponsor map

```
User → Tavily → Composio → SuperCompress → Nebius → Composio actions
```

| Sponsor | Role |
|---------|------|
| **SuperCompress** (this repo) | Compress merged context every turn |
| **Tavily** | Research blocks in context |
| **Composio** | GitHub/Gmail gather + tool execution |
| **Nebius** | Inference after compression |
| **OpenClaw** | Runtime / distribution via Harbor |

## Deadline checklist

- [ ] Public repo: https://github.com/arjunkshah/supercompress
- [ ] `./bootstrap.sh` passes on a clean machine
- [ ] Demo video shows `compare_policies` + Harbor loop
- [ ] X/LinkedIn post with repo link
- [ ] Luma submission form

See [SUBMISSION.md](SUBMISSION.md) for copy-paste fields.
