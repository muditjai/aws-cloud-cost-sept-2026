from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from agents import Runner

from .agent import create_cost_agent
from .tools.tools_main import AwsToolConfig, prepare_output_dirs


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CliOptions:
    start: str
    end: str
    forecast_start: str
    forecast_end: str
    granularity: str
    group_by: str
    filter_json: str | None
    profile: str | None
    region: str
    max_pages: int
    top_drivers: int
    project_root: Path
    assessment_dir: Path
    optimization_script_dir: Path
    out: Path | None
    apply: bool
    enable_mutations: bool
    model: str | None
    access_key_id: str | None
    secret_access_key: str | None
    session_token: str | None


def _date_string(value: date) -> str:
    return value.isoformat()


def _default_start() -> str:
    return _date_string(date.today() - timedelta(days=30))


def _default_end() -> str:
    return _date_string(date.today())


def _default_forecast_start(end: str) -> str:
    return end


def _default_forecast_end(end: str) -> str:
    parsed_end = date.fromisoformat(end)
    return _date_string(parsed_end + timedelta(days=30))


def _resolve_under_project(project_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path

    return project_root / path


def parse_args(argv: list[str] | None = None) -> CliOptions:
    parser = argparse.ArgumentParser(
        description="Run an OpenAI Agents SDK agent that analyzes AWS cloud costs.",
    )
    parser.add_argument("--start", default=_default_start(), help="Inclusive Cost Explorer start date, YYYY-MM-DD.")
    parser.add_argument("--end", default=_default_end(), help="Exclusive Cost Explorer end date, YYYY-MM-DD.")
    parser.add_argument("--forecast-start", help="Inclusive forecast start date, YYYY-MM-DD. Defaults to --end.")
    parser.add_argument("--forecast-end", help="Exclusive forecast end date, YYYY-MM-DD. Defaults to 30 days after --end.")
    parser.add_argument("--granularity", choices=["DAILY", "MONTHLY"], default="DAILY")
    parser.add_argument("--group-by", default="SERVICE", help="Comma-separated Cost Explorer dimensions.")
    parser.add_argument("--filter-json", help="Raw Cost Explorer Expression JSON.")
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"), help="AWS profile name. Defaults to AWS_PROFILE.")
    parser.add_argument("--aws-access-key-id", default=os.getenv("AWS_ACCESS_KEY_ID"), help="AWS access key ID.")
    parser.add_argument("--aws-secret-access-key", default=os.getenv("AWS_SECRET_ACCESS_KEY"), help="AWS secret access key.")
    parser.add_argument("--aws-session-token", default=os.getenv("AWS_SESSION_TOKEN"), help="Optional AWS session token.")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"), help="AWS API region.")
    parser.add_argument("--max-pages", type=int, default=4, help="Maximum paginated pages per tool call.")
    parser.add_argument("--top-drivers", type=int, default=5, help="Number of top drivers to send to service sub-agents.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT, help="Project root for tools/tools.md and artifacts.")
    parser.add_argument("--assessment-dir", type=Path, default=Path("assessment"), help="Markdown assessment output folder.")
    parser.add_argument(
        "--optimization-script-dir",
        type=Path,
        default=Path("optmization_script"),
        help="Folder for considered optimization action code files.",
    )
    parser.add_argument("--out", type=Path, help="Optional final markdown report output path.")
    parser.add_argument("--apply", action="store_true", help="Allow the agent to stage change plans. Does not mutate AWS.")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL"), help="Optional OpenAI model name.")
    args = parser.parse_args(argv)

    if args.max_pages < 1:
        parser.error("--max-pages must be greater than 0.")

    if args.top_drivers < 1:
        parser.error("--top-drivers must be greater than 0.")

    if bool(args.aws_access_key_id) != bool(args.aws_secret_access_key):
        parser.error("--aws-access-key-id and --aws-secret-access-key must be supplied together.")

    date.fromisoformat(args.start)
    date.fromisoformat(args.end)

    forecast_start = args.forecast_start or _default_forecast_start(args.end)
    forecast_end = args.forecast_end or _default_forecast_end(args.end)
    date.fromisoformat(forecast_start)
    date.fromisoformat(forecast_end)

    project_root = args.project_root.resolve()

    return CliOptions(
        start=args.start,
        end=args.end,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
        granularity=args.granularity,
        group_by=args.group_by,
        filter_json=args.filter_json,
        profile=args.profile,
        region=args.region,
        max_pages=args.max_pages,
        top_drivers=args.top_drivers,
        project_root=project_root,
        assessment_dir=_resolve_under_project(project_root, args.assessment_dir),
        optimization_script_dir=_resolve_under_project(project_root, args.optimization_script_dir),
        out=_resolve_under_project(project_root, args.out) if args.out else None,
        apply=args.apply,
        enable_mutations=os.getenv("AWS_COST_AGENT_ENABLE_MUTATIONS") == "true",
        model=args.model,
        access_key_id=args.aws_access_key_id,
        secret_access_key=args.aws_secret_access_key,
        session_token=args.aws_session_token,
    )


def build_prompt(options: CliOptions) -> str:
    filter_text = (
        f"Use this Cost Explorer filter JSON exactly: {options.filter_json}."
        if options.filter_json
        else "Do not apply an additional Cost Explorer filter."
    )
    apply_text = (
        "This run may stage change plans, but it must not mutate AWS resources unless a specific mutating tool exists and reports success."
        if options.apply
        else "This is an analysis-only run. Do not attempt AWS mutations."
    )

    return f"""
Analyze AWS cloud costs for {options.start} through {options.end}; Cost Explorer end dates are exclusive.

Use cost granularity {options.granularity}.
Group primary spend analysis by {options.group_by}.
Forecast spend from {options.forecast_start} through {options.forecast_end}.
Analyze the top {options.top_drivers} service/SKU cost drivers with specialist sub-agents.
Write Markdown assessment artifacts under {options.assessment_dir}.
Write all considered optimization actions as Python data under {options.optimization_script_dir}/considered_actions.py.
{filter_text}
{apply_text}

Required tool usage:
1. Call read_tools_registry before any AWS API call.
2. Call get_account_identity.
3. Call get_top_cost_drivers for account-level SERVICE drivers.
4. Call get_top_cost_drivers for SERVICE,USAGE_TYPE drivers to approximate service/SKU drivers.
5. Call get_cost_and_usage for the requested group-by dimensions.
6. Call get_cost_and_usage by REGION.
7. Call get_cost_forecast for the forecast period.
8. Call AWS-native recommendation tools where relevant.
9. Spawn analyze_service_cost_driver once for each of the top {options.top_drivers} service/SKU drivers.
10. Write assessment/total-cost.md and one service/SKU Markdown file per specialist result with write_assessment_file.
11. If tools/tools.md lacks a tool needed for deeper analysis, use web search to identify the AWS API and call record_proposed_tool.
12. Use stage_change_plan for every optimization action you are considering, even if it needs human approval.

Do not include AWS access keys, secrets, tokens, or credential material in any prompt output or artifact.
"""


async def async_main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")

    config = AwsToolConfig(
        profile=options.profile,
        region=options.region,
        max_pages=options.max_pages,
        enable_mutations=options.enable_mutations,
        project_root=options.project_root,
        assessment_dir=options.assessment_dir,
        optimization_script_dir=options.optimization_script_dir,
        access_key_id=options.access_key_id,
        secret_access_key=options.secret_access_key,
        session_token=options.session_token,
    )
    prepare_output_dirs(config)

    agent = create_cost_agent(config, model=options.model)
    result = await Runner.run(agent, build_prompt(options))
    output = str(result.final_output or "")

    print(output)

    final_report_path = options.out or options.assessment_dir / "final-report.md"
    final_report_path.parent.mkdir(parents=True, exist_ok=True)
    final_report_path.write_text(output, encoding="utf-8")
    print(f"[aws-cloud-cost-agent] Wrote final report to {final_report_path}")

    return 0


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(asyncio.run(async_main(argv)))
