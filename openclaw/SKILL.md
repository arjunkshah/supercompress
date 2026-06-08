---
name: supercompress
description: Builder stack — integration picks, agent prompts, and cross-app ops via Composio + Tavily + Nebius with SuperCompress memory.
metadata:
  openclaw:
    emoji: "🗜️"
    requires:
      bins: ["supercompress", "python3"]
---

# SuperCompress Agent Skill

SuperCompress is a **builder stack** for vibe coders — not a single prompt. OpenClaw can call SuperCompress; SuperCompress owns memory, integrations, and run history.

## What SuperCompress adds beyond OpenClaw

- **SuperCompress** — trims context before every Nebius turn (~35–65% KV savings)
- **Integration choice** — enable GitHub-only or add Linear/Gmail/Slack via `supercompress integrations`
- **Prompt transparency** — view system + dynamic task prompts per workflow
- **Progress** — run history, turn logs, actions in workspace output

## Commands

```bash
supercompress setup              # API keys + pick integrations + OAuth
supercompress integrations list  # see enabled vs connected
supercompress integrations set github,linear,gmail
supercompress doctor
supercompress brief
supercompress incident "..."
```

## OpenClaw bridge (optional)

SuperCompress is not OpenClaw. Use the bridge when you want OpenClaw to trigger SuperCompress workflows:

```bash
supercompress serve
# POST http://127.0.0.1:8787/openclaw/chat
```

## Environment

See `.env.example`. Required: `NEBIUS_API_KEY`, `COMPOSIO_API_KEY`, `TAVILY_API_KEY`.  
Optional: `COMPOSIO_TOOLKITS=github,linear,gmail` (add `slack` only if needed).
