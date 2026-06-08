# BuilderShip — SuperCompress submission

**Product:** Agent memory layer + full sponsor stack in one repo.

**Pitch:** OpenClaw is where agents live. SuperCompress is why they don't forget at turn 4.

## Sponsor flow (done)

```
User → Tavily → Composio → SuperCompress → Nebius → Composio
```

## 60-second demo (no keys)

```bash
./setup.sh
./bin/supercompress loop
```

**Say:** "Watch the full stack — gather, compress, infer, act. KV savings every turn."

## Live demo (your keys)

```bash
supercompress setup
supercompress connect github gmail --wait
supercompress doctor
supercompress loop --live
supercompress brief --live
```

## OpenClaw

```bash
supercompress serve
# POST http://127.0.0.1:8787/openclaw/chat
# Skill: openclaw/SKILL.md
```

## Deadline checklist

- [x] Public repo with full sponsor loop
- [x] `./bootstrap.sh` + `supercompress loop` demo
- [x] CI runs tests + loop smoke
- [ ] Demo video recorded
- [ ] X/LinkedIn post
- [ ] Luma submission

## Credits

See `.env.example` — Nebius, Composio, Tavily keys from [ship.builders](https://ship.builders).
