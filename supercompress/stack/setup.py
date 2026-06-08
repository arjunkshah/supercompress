"""Interactive setup — API keys, toolkits, checkpoint, doctor."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from supercompress.stack._paths import ROOT
from supercompress.stack.integrations import SOLO_DEFAULT_TOOLKITS

ENV_EXAMPLE = ROOT / ".env.example"
ENV_FILE = ROOT / ".env"

console = Console()

ENV_FIELDS = [
    ("NEBIUS_API_KEY", "Nebius Token Factory API key", True, "https://tokenfactory.nebius.com"),
    ("COMPOSIO_API_KEY", "Composio API key", True, "https://dashboard.composio.dev"),
    ("TAVILY_API_KEY", "Tavily API key", True, "https://app.tavily.com"),
    ("NEBIUS_MODEL", "Nebius model ID", False, "moonshotai/Kimi-K2.5"),
    ("HARBOR_USER_ID", "Composio user ID", False, "supercompress-builder-001"),
    ("COMPOSIO_TOOLKITS", "Apps (comma-separated)", False, ",".join(SOLO_DEFAULT_TOOLKITS)),
]


def _read_env() -> Dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    out: Dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def _write_env(values: Dict[str, str]) -> None:
    lines_out: list[str] = []
    seen: set[str] = set()
    if ENV_EXAMPLE.exists():
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                lines_out.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            seen.add(key)
            val = values.get(key)
            lines_out.append(f"{key}={val}" if val is not None else line)
    for key, val in values.items():
        if key not in seen:
            lines_out.append(f"{key}={val}")
    ENV_FILE.write_text("\n".join(lines_out) + "\n", encoding="utf-8")


def _mask(value: str) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return "****"
    return value[:4] + "…" + value[-4:]


def run_setup() -> None:
    console.print(Panel.fit("[bold]SuperCompress setup[/bold]\nBuilderShip sponsor keys + OAuth", border_style="cyan"))
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        console.print("[dim]Created .env from .env.example[/dim]\n")

    values = _read_env()
    for key, label, required, url in ENV_FIELDS:
        current = values.get(key, "")
        console.print(f"[bold]{key}[/bold] — {label}")
        console.print(f"  [dim]{url}[/dim]")
        console.print(f"  current: [cyan]{_mask(current)}[/cyan]")
        if required and not current:
            new = Prompt.ask("  Enter value", password="KEY" in key)
            if new.strip():
                values[key] = new.strip()
        else:
            new = Prompt.ask("  Enter new value (blank = keep)", default="", show_default=False, password="KEY" in key)
            if new.strip():
                values[key] = new.strip()
        console.print()

    values["HARBOR_DEMO"] = "0"
    _write_env(values)
    console.print("[green]✓ Saved .env[/green]\n")

    ckpt = ROOT / "checkpoints" / "default.pt"
    if not ckpt.exists():
        console.print("[yellow]Training memory checkpoint…[/yellow]")
        subprocess.run(["supercompress-train", "--fast"], check=False)

    if Confirm.ask("Connect Composio OAuth now? (github, gmail)", default=True):
        from supercompress.stack.composio import get_composio
        from supercompress.stack.config import get_settings

        get_settings.cache_clear()
        c = get_composio()
        for slug in ("github", "gmail"):
            result = c.auth_connect(slug)
            if result.redirect_url:
                console.print(f"\n[cyan]{slug}[/cyan]: {result.redirect_url}\n")
            elif result.already_connected:
                console.print(f"[green]✓ {slug} connected[/green]")

    console.print("\n[bold]Next:[/bold]")
    console.print("  supercompress doctor")
    console.print("  supercompress loop --live")
    console.print("  supercompress serve   # OpenClaw webhook")
