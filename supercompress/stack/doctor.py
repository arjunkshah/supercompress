"""Health checks for the full SuperCompress stack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rich.console import Console
from rich.table import Table

from supercompress import compare_policies
from supercompress.stack._paths import OPENCLAW_SKILL, ROOT
from supercompress.stack.composio import get_composio
from supercompress.stack.config import Settings, get_settings
from supercompress.stack.nebius import get_nebius
from supercompress.stack.nebius.models import DEFAULT_NEBIUS_MODEL
from supercompress.stack.tavily import get_tavily

console = Console()


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def run_doctor_checks(settings: Settings | None = None) -> List[CheckResult]:
    s = settings or get_settings()
    results: List[CheckResult] = []

    try:
        sample = "def authenticate(user):\n    return user.is_active\n\n" * 40
        sample += "class User:\n    def fetch(self):\n        pass\n"
        cmp = compare_policies(sample, "where is authenticate defined", budget_ratio=s.harbor_memory_budget)
        fifo = cmp["FIFO"]
        sc = cmp["SuperCompress"]
        results.append(
            CheckResult(
                "SuperCompress memory",
                True,
                f"FIFO kept {fifo.kept_tokens} tok, SuperCompress {sc.kept_tokens} tok ({sc.policy_name})",
            )
        )
    except Exception as exc:
        results.append(CheckResult("SuperCompress memory", False, str(exc)))

    try:
        t = get_tavily(s)
        bundle = t.search("OpenClaw agent runtime")
        results.append(
            CheckResult("Tavily search", True, f"{len(bundle.hits)} hits for smoke query")
        )
    except Exception as exc:
        results.append(CheckResult("Tavily search", False, str(exc)))

    oauth_ok = True
    missing_oauth: list[str] = []
    try:
        c = get_composio(s)
        summary = c.connection_summary()
        tools = c.get_openai_tools()
        missing_oauth = summary.get("missing_oauth") or []
        linked = summary.get("linked") or []
        oauth_ok = not missing_oauth or s.demo_mode
        if missing_oauth and not s.demo_mode:
            detail = (
                f"{len(tools)} tools loaded · linked: {', '.join(linked) or 'none'} · "
                f"OAuth needed: {', '.join(missing_oauth)} — run supercompress connect {' '.join(missing_oauth)}"
            )
        else:
            detail = f"{len(tools)} tools loaded, connected: {', '.join(linked) or 'demo/fixtures'}"
        results.append(CheckResult("Composio toolkits", True, detail))

        if linked and not s.demo_mode:
            gh = c.gather_github()
            if gh.prs_needing_review or gh.open_issues or gh.recent_commits:
                results.append(
                    CheckResult(
                        "GitHub snapshot",
                        True,
                        f"{len(gh.prs_needing_review)} PRs, {len(gh.open_issues)} issues, {len(gh.recent_commits)} commits",
                    )
                )
    except Exception as exc:
        oauth_ok = False
        results.append(CheckResult("Composio toolkits", False, str(exc)))

    if not s.demo_mode:
        results.append(
            CheckResult(
                "Composio OAuth",
                oauth_ok,
                "All enabled apps linked"
                if oauth_ok
                else f"Run: supercompress connect {' '.join(missing_oauth or ['github'])} --wait",
            )
        )

    try:
        n = get_nebius(s)
        resp = n.chat([{"role": "user", "content": "Reply with exactly: supercompress-ok"}])
        ok = "supercompress" in resp.content.lower() or s.demo_mode
        model_note = resp.model if resp.model != s.nebius_model else s.nebius_model
        results.append(
            CheckResult(
                "Nebius inference",
                ok,
                f"model={model_note}, tokens={resp.usage.get('total_tokens', '?')}",
            )
        )
    except Exception as exc:
        hint = f" (try NEBIUS_MODEL={DEFAULT_NEBIUS_MODEL})" if not s.demo_mode else ""
        results.append(CheckResult("Nebius inference", False, f"{exc}{hint}"))

    env_file = ROOT / ".env"
    env_ok = s.demo_mode or (env_file.exists() and s.has_live_stack())
    results.append(
        CheckResult(
            "Environment",
            env_ok,
            "demo mode" if s.demo_mode else (".env configured" if env_file.exists() else "Run: supercompress setup"),
        )
    )
    results.append(
        CheckResult(
            "OpenClaw skill",
            OPENCLAW_SKILL.exists(),
            "SKILL.md ready" if OPENCLAW_SKILL.exists() else "SKILL.md missing",
        )
    )
    return results


def run_doctor(settings: Settings | None = None, *, fix: bool = False) -> bool:
    if fix:
        console.print("[yellow]--fix is not available in SuperCompress stack doctor.[/yellow]")

    s = settings or get_settings()
    results = run_doctor_checks(s)

    table = Table(title="SuperCompress Doctor")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Detail")
    all_ok = True
    for r in results:
        if not r.ok:
            all_ok = False
        table.add_row(r.name, "✅" if r.ok else "❌", r.detail)
    console.print(table)

    mode = "DEMO" if s.demo_mode else "LIVE"
    console.print(f"\n[bold]Mode:[/bold] {mode}")
    if s.demo_mode:
        console.print("[dim]Run [cyan]supercompress setup[/cyan] for live stack.[/dim]")
    elif not all_ok:
        console.print(
            "[dim]Run [cyan]supercompress connect github gmail[/cyan] for OAuth.[/dim]"
        )
    return all_ok
