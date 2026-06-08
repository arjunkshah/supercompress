# Twitter launch kit

## 3 sentences (pin this)

**SuperCompress is the memory layer for AI agents — it compresses web search and app data before every LLM call so multi-turn agents don't blow up at turn 4.** Tavily and Composio keep stuffing context; Nebius has to read it; we trim the pile with a learned policy (~65% KV savings). Open source, `pip install`, full demo: github.com/arjunkshah/supercompress

---

## Main tweet (copy-paste)

```
Your agent forgets at turn 4. Not a prompt problem — a memory problem.

Every turn: Tavily search + Composio tools = context explosion.
SuperCompress trims what matters BEFORE inference.

~65% KV savings. Open source.

./setup.sh && ./bin/supercompress turns

github.com/arjunkshah/supercompress
```

---

## Thread (optional)

**1/** Agents feel magic on turn 1. By turn 4 they forget, hallucinate, or time out.

Not because the model got dumber — because Tavily + Composio stuffed 50 pages of context into one prompt.

**2/** We built SuperCompress: a learned eviction layer between *gather* and *inference*.

Keeps PR #42. Drops duplicate search snippets. Runs every turn automatically.

**3/** Full stack demo (not a library slide):
Tavily → Composio → SuperCompress → Nebius → Composio actions

`./bin/supercompress loop` — no keys needed for demo mode.

**4/** For builders:
```python
compressed, stats = compress_for_turn(blocks, query)
# stats.kv_savings_pct → ~65%
```

pip install · OpenClaw SKILL.md · MIT

**5/** Site: https://arjunkshah.github.io/supercompress/
Repo: https://github.com/arjunkshah/supercompress

Star if turn 4 ever ruined your agent loop 🗜️

---

## Video clip (15s screen record)

1. Terminal: `./bin/supercompress turns` (show turn 1→4 bars)
2. Cut to: `./bin/supercompress loop` (KV savings line)
3. End card: github.com/arjunkshah/supercompress

---

## GitHub repo description

```
Agent memory layer — compress context before inference. Turn 4 problem. ~65% KV savings. Tavily + Composio + Nebius + OpenClaw.
```

---

## Hashtags (pick 2–3)

`#AIAgents` `#OpenClaw` `#BuildInPublic` `#LLM` `#OpenSource`
