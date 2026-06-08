"""CLI entrypoints for SuperCompress."""

from __future__ import annotations


def train_main() -> None:
    import runpy
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "scripts" / "train_checkpoint.py"
    runpy.run_path(str(script), run_name="__main__")
