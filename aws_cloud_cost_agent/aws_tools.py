from __future__ import annotations

import json
import pprint
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import boto3
from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError


COST_METRICS = {
    "AmortizedCost",
    "BlendedCost",
    "NetAmortizedCost",
    "NetUnblendedCost",
    "UnblendedCost",
    "UsageQuantity",
}

COST_GROUP_DIMENSIONS = {
    "AZ",
    "INSTANCE_TYPE",
    "LINKED_ACCOUNT",
    "OPERATION",
    "PURCHASE_TYPE",
    "REGION",
    "SERVICE",
    "USAGE_TYPE",
}

LOOKBACK_PERIODS = {"SEVEN_DAYS", "THIRTY_DAYS", "SIXTY_DAYS"}
PAYMENT_OPTIONS = {"NO_UPFRONT", "PARTIAL_UPFRONT", "ALL_UPFRONT"}
SAVINGS_PLAN_TYPES = {"COMPUTE_SP", "EC2_INSTANCE_SP", "SAGEMAKER_SP"}
TERM_OPTIONS = {"ONE_YEAR", "THREE_YEARS"}
ACCOUNT_SCOPES = {"PAYER", "LINKED"}
FORECAST_METRICS = {
    "AMORTIZED_COST",
    "BLENDED_COST",
    "NET_AMORTIZED_COST",
    "NET_UNBLENDED_COST",
    "UNBLENDED_COST",
}
RI_SERVICES = {
    "Amazon Elastic Compute Cloud - Compute",
    "Amazon Relational Database Service",
    "Amazon Redshift",
    "Amazon ElastiCache",
    "Amazon OpenSearch Service",
}


@dataclass(frozen=True)
class AwsToolConfig:
    profile: str | None
    region: str
    max_pages: int
    enable_mutations: bool
    project_root: Path
    assessment_dir: Path
    optimization_script_dir: Path
    access_key_id: str | None = field(default=None, repr=False)
    secret_access_key: str | None = field(default=None, repr=False)
    session_token: str | None = field(default=None, repr=False)


def _session(config: AwsToolConfig) -> boto3.Session:
    if config.access_key_id or config.secret_access_key or config.session_token:
        if not config.access_key_id or not config.secret_access_key:
            raise ValueError("AWS access key authentication requires both access key ID and secret access key.")

        return boto3.Session(
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            aws_session_token=config.session_token,
            region_name=config.region,
        )

    if config.profile:
        return boto3.Session(profile_name=config.profile, region_name=config.region)

    return boto3.Session(region_name=config.region)


def _client_error(error: Exception) -> str:
    if isinstance(error, ClientError):
        details = error.response.get("Error", {})
        code = details.get("Code", "Unknown")
        message = details.get("Message", str(error))
        return f"{code}: {message}"

    return str(error)


def _strip_metadata(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_metadata(item) for item in value]

    if isinstance(value, dict):
        return {
            key: _strip_metadata(item)
            for key, item in value.items()
            if key != "ResponseMetadata"
        }

    return value


def _json(value: Any) -> str:
    return json.dumps(_strip_metadata(value), indent=2, sort_keys=True, default=str)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "assessment"


def _safe_markdown_name(filename: str) -> str:
    name = Path(filename).name

    if not name.endswith(".md"):
        name = f"{name}.md"

    return _slug(name[:-3]) + ".md"


def _validate_all(values: list[str], allowed: set[str], label: str) -> None:
    invalid = [value for value in values if value not in allowed]

    if invalid:
        raise ValueError(f"Unsupported {label}: {', '.join(invalid)}")


def _parse_filter(filter_json: str | None) -> dict[str, Any] | None:
    if not filter_json:
        return None

    parsed = json.loads(filter_json)

    if not isinstance(parsed, dict):
        raise ValueError("filter_json must decode to a JSON object.")

    return parsed


def _service_filter(service: str, base_filter_json: str | None = None) -> dict[str, Any]:
    service_expression = {"Dimensions": {"Key": "SERVICE", "Values": [service]}}
    base_filter = _parse_filter(base_filter_json)

    if not base_filter:
        return service_expression

    return {"And": [base_filter, service_expression]}


def _collect_pages(client: Any, method_name: str, result_key: str, max_pages: int, **kwargs: Any) -> dict[str, Any]:
    items: list[Any] = []
    pages: list[dict[str, Any]] = []
    next_page_token: str | None = None

    for _ in range(max_pages):
        request = dict(kwargs)

        if next_page_token:
            request["NextPageToken"] = next_page_token

        response = getattr(client, method_name)(**request)
        page_items = response.get(result_key, [])

        pages.append(_strip_metadata(response))
        items.extend(page_items)
        next_page_token = response.get("NextPageToken")

        if not next_page_token:
            break

    return {
        "items": _strip_metadata(items),
        "pages": pages,
        "page_count": len(pages),
        "is_truncated": bool(next_page_token),
    }


def _group_amount(group: dict[str, Any], metric: str) -> float:
    amount = group.get("Metrics", {}).get(metric, {}).get("Amount", "0")

    try:
        return float(amount)
    except (TypeError, ValueError):
        return 0.0


def _summarize_cost_groups(cost_response: dict[str, Any], metric: str) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}

    for result in cost_response.get("items", []):
        for group in result.get("Groups", []):
            keys = group.get("Keys", [])
            key = " | ".join(keys) if keys else "Ungrouped"
            current = totals.setdefault(
                key,
                {
                    "key": key,
                    "keys": keys,
                    "amount": 0.0,
                    "unit": group.get("Metrics", {}).get(metric, {}).get("Unit"),
                },
            )
            current["amount"] += _group_amount(group, metric)

    return sorted(totals.values(), key=lambda item: item["amount"], reverse=True)


def _write_considered_actions(path: Path, actions: list[dict[str, Any]]) -> None:
    rendered_actions = pprint.pformat(actions, width=120, sort_dicts=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '"""Candidate AWS optimization actions generated by the cost agent.\n\n'
        "This file is review material only. It is not executed automatically.\n"
        '"""\n\n'
        f"CONSIDERED_ACTIONS = {rendered_actions}\n",
        encoding="utf-8",
    )


def prepare_output_dirs(config: AwsToolConfig) -> None:
    """Create output folders and reset per-run action artifacts."""
    config.assessment_dir.mkdir(parents=True, exist_ok=True)
    config.optimization_script_dir.mkdir(parents=True, exist_ok=True)
    (config.project_root / "proposed_tools.md").touch(exist_ok=True)
    _write_considered_actions(config.optimization_script_dir / "considered_actions.py", [])


def create_aws_tools(config: AwsToolConfig, include_artifact_tools: bool = True) -> list[Any]:
    """Create OpenAI function tools backed by AWS API calls and local artifacts."""
    session = _session(config)
    cost_explorer = session.client("ce", region_name=config.region)
    sts = session.client("sts", region_name=config.region)
    considered_actions: list[dict[str, Any]] = []

    @tool
    def read_tools_registry() -> str:
        """Read tools.md, the source-of-truth registry of tools available to this agent."""
        tools_path = config.project_root / "tools.md"

        if not tools_path.exists():
            return _json({"ok": False, "error": "tools.md does not exist."})

        return tools_path.read_text(encoding="utf-8")

    @tool
    def get_account_identity() -> str:
        """Return the AWS account identity for the credentials used by this run."""
        try:
            return _json(sts.get_caller_identity())
        except (BotoCoreError, ClientError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def get_cost_and_usage(
        start: str,
        end: str,
        granularity: str = "DAILY",
        metrics_csv: str = "UnblendedCost,UsageQuantity",
        group_by_csv: str = "SERVICE",
        filter_json: str | None = None,
    ) -> str:
        """Query AWS Cost Explorer for historical costs and usage.

        Args:
            start: Inclusive start date in YYYY-MM-DD format.
            end: Exclusive end date in YYYY-MM-DD format.
            granularity: DAILY or MONTHLY.
            metrics_csv: Comma-separated Cost Explorer metric names.
            group_by_csv: Comma-separated Cost Explorer dimension names.
            filter_json: Optional raw Cost Explorer Expression JSON.
        """
        try:
            metrics = _csv(metrics_csv)
            group_by = _csv(group_by_csv)

            _validate_all(metrics, COST_METRICS, "metrics")
            _validate_all(group_by, COST_GROUP_DIMENSIONS, "group_by dimensions")

            request = {
                "TimePeriod": {"Start": start, "End": end},
                "Granularity": granularity,
                "Metrics": metrics,
                "GroupBy": [{"Type": "DIMENSION", "Key": item} for item in group_by],
            }
            filter_expression = _parse_filter(filter_json)

            if filter_expression:
                request["Filter"] = filter_expression

            return _json(
                _collect_pages(
                    cost_explorer,
                    "get_cost_and_usage",
                    "ResultsByTime",
                    config.max_pages,
                    **request,
                )
            )
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def get_top_cost_drivers(
        start: str,
        end: str,
        granularity: str = "MONTHLY",
        group_by_csv: str = "SERVICE",
        metric: str = "UnblendedCost",
        limit: int = 5,
        filter_json: str | None = None,
    ) -> str:
        """Return the top AWS cost drivers from Cost Explorer.

        Args:
            start: Inclusive start date in YYYY-MM-DD format.
            end: Exclusive end date in YYYY-MM-DD format.
            granularity: DAILY or MONTHLY.
            group_by_csv: Comma-separated Cost Explorer dimensions.
            metric: Cost metric to rank by.
            limit: Maximum number of drivers to return.
            filter_json: Optional raw Cost Explorer Expression JSON.
        """
        try:
            _validate_all([metric], COST_METRICS, "metric")

            raw = json.loads(
                get_cost_and_usage.__wrapped__(
                    start=start,
                    end=end,
                    granularity=granularity,
                    metrics_csv=metric,
                    group_by_csv=group_by_csv,
                    filter_json=filter_json,
                )
            )

            if raw.get("ok") is False:
                return _json(raw)

            drivers = _summarize_cost_groups(raw, metric)

            return _json(
                {
                    "metric": metric,
                    "group_by": _csv(group_by_csv),
                    "top_drivers": drivers[:limit],
                    "driver_count": len(drivers),
                    "source": raw,
                }
            )
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def get_service_cost_breakdown(
        service: str,
        start: str,
        end: str,
        granularity: str = "MONTHLY",
        group_by_csv: str = "USAGE_TYPE,OPERATION",
        metric: str = "UnblendedCost",
        limit: int = 20,
        filter_json: str | None = None,
    ) -> str:
        """Break down one AWS service by usage type, operation, region, or another Cost Explorer dimension.

        Args:
            service: Exact AWS Cost Explorer SERVICE value.
            start: Inclusive start date in YYYY-MM-DD format.
            end: Exclusive end date in YYYY-MM-DD format.
            granularity: DAILY or MONTHLY.
            group_by_csv: Comma-separated Cost Explorer dimensions.
            metric: Cost metric to rank by.
            limit: Maximum number of breakdown rows to return.
            filter_json: Optional raw Cost Explorer Expression JSON combined with the service filter.
        """
        try:
            _validate_all([metric], COST_METRICS, "metric")
            service_filter = _service_filter(service, filter_json)
            raw = json.loads(
                get_cost_and_usage.__wrapped__(
                    start=start,
                    end=end,
                    granularity=granularity,
                    metrics_csv=metric,
                    group_by_csv=group_by_csv,
                    filter_json=json.dumps(service_filter),
                )
            )

            if raw.get("ok") is False:
                return _json(raw)

            drivers = _summarize_cost_groups(raw, metric)

            return _json(
                {
                    "service": service,
                    "metric": metric,
                    "group_by": _csv(group_by_csv),
                    "top_breakdown_rows": drivers[:limit],
                    "breakdown_row_count": len(drivers),
                    "source": raw,
                }
            )
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def get_cost_forecast(
        start: str,
        end: str,
        metric: str = "UNBLENDED_COST",
        granularity: str = "MONTHLY",
    ) -> str:
        """Fetch an AWS Cost Explorer forecast for a future period.

        Args:
            start: Inclusive forecast start date in YYYY-MM-DD format.
            end: Exclusive forecast end date in YYYY-MM-DD format.
            metric: Cost Explorer forecast metric.
            granularity: DAILY or MONTHLY.
        """
        try:
            _validate_all([metric], FORECAST_METRICS, "forecast metric")

            return _json(
                cost_explorer.get_cost_forecast(
                    TimePeriod={"Start": start, "End": end},
                    Metric=metric,
                    Granularity=granularity,
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def get_rightsizing_recommendations(
        page_size: int = 20,
        benefits_considered: bool = True,
        recommendation_target: str = "SAME_INSTANCE_FAMILY",
    ) -> str:
        """Fetch AWS Cost Explorer EC2 rightsizing recommendations.

        Args:
            page_size: Number of recommendations to return per page.
            benefits_considered: Whether to account for RI or Savings Plans discounts.
            recommendation_target: SAME_INSTANCE_FAMILY or CROSS_INSTANCE_FAMILY.
        """
        try:
            return _json(
                _collect_pages(
                    cost_explorer,
                    "get_rightsizing_recommendation",
                    "RightsizingRecommendations",
                    config.max_pages,
                    Service="AmazonEC2",
                    Configuration={
                        "BenefitsConsidered": benefits_considered,
                        "RecommendationTarget": recommendation_target,
                    },
                    PageSize=page_size,
                )
            )
        except (BotoCoreError, ClientError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def get_savings_plans_recommendations(
        lookback_period_in_days: str = "THIRTY_DAYS",
        payment_option: str = "NO_UPFRONT",
        savings_plans_type: str = "COMPUTE_SP",
        term_in_years: str = "ONE_YEAR",
        account_scope: str = "PAYER",
    ) -> str:
        """Fetch AWS Savings Plans purchase recommendations from Cost Explorer."""
        try:
            _validate_all([lookback_period_in_days], LOOKBACK_PERIODS, "lookback period")
            _validate_all([payment_option], PAYMENT_OPTIONS, "payment option")
            _validate_all([savings_plans_type], SAVINGS_PLAN_TYPES, "Savings Plans type")
            _validate_all([term_in_years], TERM_OPTIONS, "term")
            _validate_all([account_scope], ACCOUNT_SCOPES, "account scope")

            return _json(
                cost_explorer.get_savings_plans_purchase_recommendation(
                    LookbackPeriodInDays=lookback_period_in_days,
                    PaymentOption=payment_option,
                    SavingsPlansType=savings_plans_type,
                    TermInYears=term_in_years,
                    AccountScope=account_scope,
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def get_reservation_recommendations(
        service: str = "Amazon Elastic Compute Cloud - Compute",
        lookback_period_in_days: str = "THIRTY_DAYS",
        payment_option: str = "NO_UPFRONT",
        term_in_years: str = "ONE_YEAR",
        account_scope: str = "PAYER",
    ) -> str:
        """Fetch AWS Reserved Instance purchase recommendations from Cost Explorer."""
        try:
            _validate_all([service], RI_SERVICES, "reservation service")
            _validate_all([lookback_period_in_days], LOOKBACK_PERIODS, "lookback period")
            _validate_all([payment_option], PAYMENT_OPTIONS, "payment option")
            _validate_all([term_in_years], TERM_OPTIONS, "term")
            _validate_all([account_scope], ACCOUNT_SCOPES, "account scope")

            return _json(
                cost_explorer.get_reservation_purchase_recommendation(
                    Service=service,
                    LookbackPeriodInDays=lookback_period_in_days,
                    PaymentOption=payment_option,
                    TermInYears=term_in_years,
                    AccountScope=account_scope,
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return _json({"ok": False, "error": _client_error(error)})

    @tool
    def write_assessment_file(filename: str, markdown: str) -> str:
        """Write a markdown assessment file under the assessment folder.

        Args:
            filename: File name, not a path. The tool normalizes it to a safe .md file.
            markdown: Markdown report body.
        """
        if not include_artifact_tools:
            return _json({"ok": False, "error": "Artifact writes are disabled for this agent."})

        output_path = config.assessment_dir / _safe_markdown_name(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")

        return _json({"ok": True, "path": str(output_path)})

    @tool
    def record_proposed_tool(tool_name: str, reason: str, aws_apis: list[str], proposed_interface: str) -> str:
        """Append a missing tool proposal to proposed_tools.md.

        Args:
            tool_name: Proposed function tool name.
            reason: Why the existing tools are insufficient.
            aws_apis: AWS APIs or data sources the tool would call.
            proposed_interface: Proposed inputs and outputs for the tool.
        """
        if not include_artifact_tools:
            return _json({"ok": False, "error": "Artifact writes are disabled for this agent."})

        proposed_path = config.project_root / "proposed_tools.md"
        proposed_path.parent.mkdir(parents=True, exist_ok=True)
        with proposed_path.open("a", encoding="utf-8") as file:
            file.write(
                f"\n## {tool_name}\n\n"
                f"- Reason: {reason}\n"
                f"- AWS APIs: {', '.join(aws_apis)}\n"
                f"- Proposed interface: {proposed_interface}\n"
            )

        return _json({"ok": True, "path": str(proposed_path)})

    @tool
    def stage_change_plan(
        recommendation_id: str,
        service: str,
        proposed_action: str,
        expected_savings: str,
        risk: str,
        validation_plan: list[str],
        rollback_plan: list[str],
        region: str | None = None,
        resource_ids: list[str] | None = None,
        implementation_notes: str | None = None,
    ) -> str:
        """Stage a proposed AWS change in optmization_script/considered_actions.py without changing AWS resources."""
        if not include_artifact_tools:
            return _json({"ok": False, "error": "Change staging is disabled for this agent."})

        action = {
            "recommendation_id": recommendation_id,
            "service": service,
            "region": region,
            "resource_ids": resource_ids or [],
            "proposed_action": proposed_action,
            "expected_savings": expected_savings,
            "risk": risk,
            "validation_plan": validation_plan,
            "rollback_plan": rollback_plan,
            "implementation_notes": implementation_notes,
            "requires_human_approval": True,
            "mutation_enabled": config.enable_mutations,
        }
        considered_actions.append(action)
        path = config.optimization_script_dir / "considered_actions.py"
        _write_considered_actions(path, considered_actions)

        return _json(
            {
                "ok": True,
                "staged_only": True,
                "path": str(path),
                "message": "Change plan written for review. No AWS resources were changed.",
                "change_plan": action,
            }
        )

    tools = [
        read_tools_registry,
        get_account_identity,
        get_cost_and_usage,
        get_top_cost_drivers,
        get_service_cost_breakdown,
        get_cost_forecast,
        get_rightsizing_recommendations,
        get_savings_plans_recommendations,
        get_reservation_recommendations,
    ]

    if include_artifact_tools:
        tools.extend([write_assessment_file, record_proposed_tool, stage_change_plan])

    return tools
