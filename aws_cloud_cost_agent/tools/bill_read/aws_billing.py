from __future__ import annotations

import json
from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import (
    COST_GROUP_DIMENSIONS,
    COST_METRICS,
    AwsToolConfig,
    client_error_message,
    collect_pages,
    create_boto3_session,
    csv_values,
    json_dumps,
    parse_filter,
    validate_all,
)


def fetch_cost_and_usage(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
    group_by: str,
    filter_json: str | None = None,
) -> dict[str, Any]:
    """Fetch monthly unblended costs from AWS Cost Explorer."""
    dimensions = csv_values(group_by)
    validate_all(dimensions, COST_GROUP_DIMENSIONS, "group dimensions")
    validate_all(["UnblendedCost"], COST_METRICS, "metrics")

    request: dict[str, Any] = {
        "TimePeriod": {"Start": start_date, "End": end_date},
        "Granularity": "MONTHLY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": value} for value in dimensions],
    }
    cost_filter = parse_filter(filter_json)
    if cost_filter:
        request["Filter"] = cost_filter

    client = create_boto3_session(config).client("ce", region_name="us-east-1")
    return collect_pages(client, "get_cost_and_usage", "ResultsByTime", **request)


def create_billing_read_tools(config: AwsToolConfig) -> list[Any]:
    """Create the overall billing data tool."""

    @tool
    def get_bill_data(start_date: str, end_date: str, group_by: str = "SERVICE") -> str:
        """Read monthly AWS costs grouped by SERVICE, REGION, USAGE_TYPE, or OPERATION."""
        try:
            return json_dumps(fetch_cost_and_usage(config, start_date, end_date, group_by))
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [get_bill_data]
