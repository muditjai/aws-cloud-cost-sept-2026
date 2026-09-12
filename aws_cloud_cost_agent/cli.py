from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .steps import AVAILABLE_STEPS
from .tools.shared import AwsToolConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CliOptions:
    aws_account: str | None
    start_date: str
    end_date: str
    steps: list[str]


def load_local_env(path: Path) -> None:
    """Load local environment values without overriding exported variables."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def parse_args(argv: list[str] | None = None) -> CliOptions:
    today = date.today()
    parser = argparse.ArgumentParser(description="Assess AWS costs and write Markdown artifacts.")
    parser.add_argument(
        "--aws-account",
        default=os.getenv("AWS_ACCOUNT_ID"),
        help="Expected AWS account ID. The run stops if the credentials belong to another account.",
    )
    parser.add_argument(
        "--start-date",
        default=(today - timedelta(days=30)).isoformat(),
        help="Inclusive billing start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        default=today.isoformat(),
        help="Exclusive billing end date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=AVAILABLE_STEPS,
        default=list(AVAILABLE_STEPS),
        help="Steps to run. Defaults to all steps.",
    )
    args = parser.parse_args(argv)

    try:
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
    except ValueError as error:
        parser.error(str(error))

    if start_date >= end_date:
        parser.error("--start-date must be before --end-date.")

    return CliOptions(
        aws_account=args.aws_account,
        start_date=args.start_date,
        end_date=args.end_date,
        steps=args.steps,
    )


async def async_main(argv: list[str] | None = None) -> int:
    load_local_env(PROJECT_ROOT / ".env")
    options = parse_args(argv)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")

    from .workflow import run_workflow

    artifacts = await run_workflow(
        config=AwsToolConfig.from_environment(PROJECT_ROOT),
        expected_account=options.aws_account,
        start_date=options.start_date,
        end_date=options.end_date,
        steps=options.steps,
    )

    for artifact in artifacts:
        print(artifact)

    return 0


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(asyncio.run(async_main(argv)))
