from __future__ import annotations

from pathlib import Path


def load_prompt(path: Path, **values: str) -> str:
    """Load one step prompt and substitute its workflow values."""
    return path.read_text(encoding="utf-8").format(**values)
