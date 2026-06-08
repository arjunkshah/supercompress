"""SuperCompress CLI — train, doctor, sponsor loop, setup."""

from __future__ import annotations

import os
from typing import Optional

import typer

app = typer.Typer(
    name="supercompress",
    help="SuperCompress — agent memory layer + BuilderShip sponsor stack",
    no_args_is_help=True,
)


def train_main() -> None:
    import runpy
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "scripts" / "train_checkpoint.py"
    runpy.run_path(str(script), run_name="__main__")


@app.command("train")
def cmd_train(fast: bool = typer.Option(True, "--fast/--full", help="Quick train (~30s)")) -> None:
    """Train the learned eviction checkpoint."""
    import sys

    sys.argv = ["train_checkpoint.py", "--fast"] if fast else ["train_checkpoint.py"]
    train_main()


@app.command("doctor")
def cmd_doctor(
    fix: bool = typer.Option(False, "--fix", help="Apply .env migrations when available"),
    demo: bool = typer.Option(False, "--demo", help="Force demo mode for this run"),
) -> None:
    """Verify memory layer + Tavily + Composio + Nebius + OpenClaw skill."""
    if demo:
        os.environ["HARBOR_DEMO"] = "1"
    from supercompress.stack.config import get_settings
    from supercompress.stack.doctor import run_doctor

    get_settings.cache_clear()
    ok = run_doctor(fix=fix)
    raise typer.Exit(0 if ok else 1)


@app.command("loop")
def cmd_loop(
    task: str = typer.Option(
        "Triage my open GitHub PRs and suggest what to ship",
        "--task",
        "-t",
        help="Agent task",
    ),
    live: bool = typer.Option(False, "--live", help="Use live APIs (requires .env keys)"),
) -> None:
    """Run full sponsor loop: Tavily → Composio → SuperCompress → Nebius."""
    if live:
        os.environ.pop("HARBOR_DEMO", None)
    else:
        os.environ["HARBOR_DEMO"] = "1"

    from supercompress.stack.config import get_settings
    from supercompress.stack.demo_loop import run_loop

    get_settings.cache_clear()
    raise typer.Exit(run_loop(task=task, live=live))


@app.command("brief")
def cmd_brief(
    company: str = typer.Option("OpenClaw", help="Company for intel"),
    focus: str = typer.Option("agent builders", help="Research focus"),
    live: bool = typer.Option(False, "--live"),
) -> None:
    """Morning brief workflow across the full stack."""
    if live:
        os.environ.pop("HARBOR_DEMO", None)
    else:
        os.environ["HARBOR_DEMO"] = "1"

    from supercompress.stack.agent.loop import StackAgent
    from supercompress.stack.config import get_settings

    get_settings.cache_clear()
    result = StackAgent().morning_brief(company=company, focus=focus)
    typer.echo(result.summary or "(no summary)")
    typer.echo(f"\nKV savings: {result.memory_savings_pct:.1f}%")
    typer.echo(f"Actions: {len(result.actions_taken)}")


@app.command("incident")
def cmd_incident(
    query: str = typer.Argument(..., help="Incident description"),
    service: str = typer.Option("production API", "--service"),
    live: bool = typer.Option(False, "--live"),
) -> None:
    """Incident commander workflow."""
    if live:
        os.environ.pop("HARBOR_DEMO", None)
    else:
        os.environ["HARBOR_DEMO"] = "1"

    from supercompress.stack.agent.loop import StackAgent
    from supercompress.stack.config import get_settings

    get_settings.cache_clear()
    result = StackAgent().incident_commander(query, service_name=service)
    typer.echo(result.summary or "(no summary)")


@app.command("setup")
def cmd_setup() -> None:
    """Interactive API key setup + OAuth connect."""
    from supercompress.stack.setup import run_setup

    run_setup()


@app.command("connect")
def cmd_connect(
    toolkits: list[str] = typer.Argument(..., help="Toolkits: github gmail slack ..."),
    wait: bool = typer.Option(False, "--wait", help="Poll until OAuth completes"),
) -> None:
    """OAuth connect for Composio toolkits."""
    from supercompress.stack.composio import get_composio
    from supercompress.stack.config import get_settings

    get_settings.cache_clear()
    c = get_composio()
    for tk in toolkits:
        if wait:
            result = c.wait_for_connection(tk)
        else:
            result = c.auth_connect(tk)
        if result.already_connected:
            typer.echo(f"✓ {tk} already connected")
        elif result.redirect_url:
            typer.echo(f"Open to connect {tk}: {result.redirect_url}")
        elif result.error:
            typer.echo(f"✗ {tk}: {result.error}", err=True)


@app.command("demo")
def cmd_demo() -> None:
    """Quick compression demo (no sponsor keys)."""
    import runpy
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "examples" / "demo_compare.py"
    runpy.run_path(str(script), run_name="__main__")


@app.command("turns")
def cmd_turns() -> None:
    """Turn 4 demo — context growth vs SuperCompress (best for Twitter/video)."""
    from supercompress.stack.turn4_demo import run_turn4_demo

    raise typer.Exit(run_turn4_demo())


@app.command("serve")
def cmd_serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Start API + OpenClaw webhook bridge."""
    import uvicorn

    uvicorn.run("supercompress.stack.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
