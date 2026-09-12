from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError


COST_METRICS = {
    "AmortizedCost", "BlendedCost", "NetAmortizedCost", "NetUnblendedCost",
    "UnblendedCost", "UsageQuantity",
}
COST_GROUP_DIMENSIONS = {
    "AZ", "INSTANCE_TYPE", "LINKED_ACCOUNT", "OPERATION",
    "PURCHASE_TYPE", "REGION", "RESOURCE_ID", "SERVICE", "USAGE_TYPE",
}
@dataclass(frozen=True)
class AwsToolConfig:
    project_root: Path
    region: str = "us-east-1"
    profile: str | None = None
    access_key_id: str | None = field(default=None, repr=False)
    secret_access_key: str | None = field(default=None, repr=False)
    session_token: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls, project_root: Path) -> "AwsToolConfig":
        return cls(
            project_root=project_root,
            region=os.getenv("AWS_REGION", "us-east-1"),
            profile=os.getenv("AWS_PROFILE"),
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            session_token=os.getenv("AWS_SESSION_TOKEN"),
        )

    @property
    def output_dir(self) -> Path:
        return self.project_root / "output_artifact"

    @property
    def tools_dir(self) -> Path:
        return self.project_root / "aws_cloud_cost_agent" / "tools"


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
        return f"{details.get('Code', 'Unknown')}: {details.get('Message', str(error))}"

    return str(error)


def strip_metadata(value: Any) -> Any:
    if isinstance(value, list):
        return [strip_metadata(item) for item in value]
    if isinstance(value, dict):
        return {key: strip_metadata(item) for key, item in value.items() if key != "ResponseMetadata"}
    return value


def json_dumps(value: Any) -> str:
    return json.dumps(strip_metadata(value), indent=2, sort_keys=True, default=str)


def csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_") or "unknown"


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


def service_filter(service: str) -> dict[str, Any]:
    return {"Dimensions": {"Key": "SERVICE", "Values": [service]}}


def collect_pages(client: Any, method_name: str, result_key: str, **kwargs: Any) -> dict[str, Any]:
    items: list[Any] = []
    pages: list[dict[str, Any]] = []
    next_page_token: str | None = None

    for _ in range(4):
        request = dict(kwargs)
        if next_page_token:
            request["NextPageToken"] = next_page_token

        response = getattr(client, method_name)(**request)
        items.extend(response.get(result_key, []))
        pages.append(strip_metadata(response))
        next_page_token = response.get("NextPageToken")
        if not next_page_token:
            break

    return {"items": strip_metadata(items), "pages": pages, "is_truncated": bool(next_page_token)}


def summarize_cost_groups(cost_response: dict[str, Any], metric: str) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}

    for result in cost_response.get("items", []):
        for group in result.get("Groups", []):
            keys = group.get("Keys", [])
            key = " | ".join(keys) if keys else "Ungrouped"
            metric_data = group.get("Metrics", {}).get(metric, {})
            try:
                amount = float(metric_data.get("Amount", "0"))
            except (TypeError, ValueError):
                amount = 0.0

            current = totals.setdefault(
                key,
                {"key": key, "keys": keys, "amount": 0.0, "unit": metric_data.get("Unit")},
            )
            current["amount"] += amount

    return sorted(totals.values(), key=lambda item: item["amount"], reverse=True)
