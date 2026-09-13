from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from .agent import RESPAN_MODEL, run_markdown_agent
from .prompt_loader import load_prompt
from .tools.auth.aws_auth import get_account_identity_data, render_connection_check
from .tools.bill_read.aws_billing import build_overall_bill_report
from .tools.cost_analysis.cloudfront import CLOUDFRONT_SERVICE
from .tools.cost_analysis.elb import ELB_SERVICE
from .tools.cost_analysis.per_technology import discover_top_service_skus
from .tools.cost_analysis.rds import RDS_SERVICE
from .tools.shared import AwsToolConfig, slug
from .tools.tools_main import (
    recommendation_tools,
    service_analysis_tools,
)


def _write_artifact(output_dir: Path, filename: str, markdown: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = markdown.rstrip().splitlines()
    timestamp_line = f"**Analysis timestamp (UTC):** `{timestamp}`"
    if lines and lines[0].startswith("# "):
        lines = [lines[0], "", timestamp_line, "", *lines[1:]]
    else:
        lines = [timestamp_line, "", *lines]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _service_values(driver: dict) -> tuple[str, str]:
    keys = driver.get("keys", [])
    service = keys[0] if keys else "Unknown service"
    sku = keys[1] if len(keys) > 1 else "Unknown usage type"
    return service, sku


async def run_workflow(
    config: AwsToolConfig,
    expected_account: str | None,
    start_date: str,
    end_date: str,
    steps: list[str],
    respan_model: str = RESPAN_MODEL,
) -> list[Path]:
    """Run selected assessment steps and return generated artifact paths."""
    identity = get_account_identity_data(config)
    actual_account = identity["Account"]

    prompts = config.tools_dir
    common = {
        "account_id": actual_account,
        "start_date": start_date,
        "end_date": end_date,
    }
    artifacts: list[Path] = []

    if "connection-check" in steps:
        markdown = render_connection_check(identity, expected_account, config.region)
        artifacts.append(
            _write_artifact(
                config.output_dir,
                f"connection_check_{date.today().isoformat()}.md",
                markdown,
            )
        )

    if expected_account and expected_account != actual_account:
        raise RuntimeError(
            f"AWS account mismatch: expected {expected_account}, credentials belong to {actual_account}."
        )

    if "overall-bill" in steps:
        markdown = build_overall_bill_report(config, actual_account, start_date, end_date)
        artifacts.append(
            _write_artifact(
                config.output_dir,
                f"overall_bill_data_{start_date}_{end_date}.md",
                markdown,
            )
        )

    service_steps = {"service-analysis", "recommendations"}.intersection(steps)
    drivers = discover_top_service_skus(config, start_date, end_date) if service_steps else []

    for driver in drivers:
        service, sku = _service_values(driver)
        values = {
            **common,
            "service": service,
            "sku": sku,
            "cost": f"{driver['amount']:.2f} {driver.get('unit') or 'USD'}",
        }
        artifact_suffix = f"{slug(service)}_{slug(sku)}_{start_date}_{end_date}.md"

        if "service-analysis" in steps:
            prompt_name = {
                ELB_SERVICE: "elb_analysis_prompt.md",
                RDS_SERVICE: "rds_analysis_prompt.md",
                CLOUDFRONT_SERVICE: "cloudfront_analysis_prompt.md",
            }.get(service, "service_sku_analysis_prompt.md")
            prompt = load_prompt(
                prompts / "cost_analysis" / prompt_name,
                **values,
            )
            markdown = await run_markdown_agent(
                f"AWS cost analysis: {service} / {sku}",
                prompt,
                service_analysis_tools(config, service),
                model=respan_model,
            )
            artifacts.append(
                _write_artifact(
                    config.output_dir,
                    f"service_sku_analysis_{artifact_suffix}",
                    markdown,
                )
            )

        if "recommendations" in steps:
            prompt = load_prompt(
                prompts / "cost_recommendation" / "service_sku_recommendation_prompt.md",
                **values,
            )
            markdown = await run_markdown_agent(
                f"AWS recommendations: {service} / {sku}",
                prompt,
                recommendation_tools(config),
                use_web_search=True,
                model=respan_model,
            )
            artifacts.append(
                _write_artifact(
                    config.output_dir,
                    f"recommendations_{artifact_suffix}",
                    markdown,
                )
            )

    return artifacts
