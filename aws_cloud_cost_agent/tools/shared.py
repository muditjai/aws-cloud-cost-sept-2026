from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError


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

    @property
    def tools_dir(self) -> Path:
        return self.project_root / "tools"

    @property
    def tools_registry_path(self) -> Path:
        return self.tools_dir / "tools.md"

    @property
    def proposed_tools_path(self) -> Path:
        return self.tools_dir / "proposed_tools.md"


def create_boto3_session(config: AwsToolConfig) -> boto3.Session:
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


def client_error_message(error: Exception) -> str:
    if isinstance(error, ClientError):
        details = error.response.get("Error", {})
        code = details.get("Code", "Unknown")
        message = details.get("Message", str(error))
        return f"{code}: {message}"

    return str(error)


def strip_metadata(value: Any) -> Any:
    if isinstance(value, list):
        return [strip_metadata(item) for item in value]

    if isinstance(value, dict):
        return {
            key: strip_metadata(item)
            for key, item in value.items()
            if key != "ResponseMetadata"
        }

    return value


def json_dumps(value: Any) -> str:
    return json.dumps(strip_metadata(value), indent=2, sort_keys=True, default=str)


def csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return normalized or "assessment"


def safe_markdown_name(filename: str) -> str:
    name = Path(filename).name

    if not name.endswith(".md"):
        name = f"{name}.md"

    return slug(name[:-3]) + ".md"


def validate_all(values: list[str], allowed: set[str], label: str) -> None:
    invalid = [value for value in values if value not in allowed]

    if invalid:
        raise ValueError(f"Unsupported {label}: {', '.join(invalid)}")


def parse_filter(filter_json: str | None) -> dict[str, Any] | None:
    if not filter_json:
        return None

    parsed = json.loads(filter_json)

    if not isinstance(parsed, dict):
        raise ValueError("filter_json must decode to a JSON object.")

    return parsed


def service_filter(service: str, base_filter_json: str | None = None) -> dict[str, Any]:
    service_expression = {"Dimensions": {"Key": "SERVICE", "Values": [service]}}
    base_filter = parse_filter(base_filter_json)

    if not base_filter:
        return service_expression

    return {"And": [base_filter, service_expression]}


def collect_pages(client: Any, method_name: str, result_key: str, max_pages: int, **kwargs: Any) -> dict[str, Any]:
    items: list[Any] = []
    pages: list[dict[str, Any]] = []
    next_page_token: str | None = None

    for _ in range(max_pages):
        request = dict(kwargs)

        if next_page_token:
            request["NextPageToken"] = next_page_token

        response = getattr(client, method_name)(**request)
        page_items = response.get(result_key, [])

        pages.append(strip_metadata(response))
        items.extend(page_items)
        next_page_token = response.get("NextPageToken")

        if not next_page_token:
            break

    return {
        "items": strip_metadata(items),
        "pages": pages,
        "page_count": len(pages),
        "is_truncated": bool(next_page_token),
    }


def summarize_cost_groups(cost_response: dict[str, Any], metric: str) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}

    for result in cost_response.get("items", []):
        for group in result.get("Groups", []):
            keys = group.get("Keys", [])
            key = " | ".join(keys) if keys else "Ungrouped"
            amount = group.get("Metrics", {}).get(metric, {}).get("Amount", "0")

            try:
                parsed_amount = float(amount)
            except (TypeError, ValueError):
                parsed_amount = 0.0

            current = totals.setdefault(
                key,
                {
                    "key": key,
                    "keys": keys,
                    "amount": 0.0,
                    "unit": group.get("Metrics", {}).get(metric, {}).get("Unit"),
                },
            )
            current["amount"] += parsed_amount

    return sorted(totals.values(), key=lambda item: item["amount"], reverse=True)
