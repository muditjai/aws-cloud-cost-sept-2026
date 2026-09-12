from __future__ import annotations

import json
from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import (
    COST_GROUP_DIMENSIONS,
    COST_METRICS,
    FORECAST_METRICS,
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
    cost_explorer: Any,
    config: AwsToolConfig,
    start: str,
    end: str,
    granularity: str = "DAILY",
    metrics_csv: str = "UnblendedCost,UsageQuantity",
    group_by_csv: str = "SERVICE",
    filter_json: str | None = None,
) -> dict[str, Any]:
    """Fetch Cost Explorer cost and usage data and return normalized JSON-ready data."""
    metrics = csv_values(metrics_csv)
    group_by = csv_values(group_by_csv)

    validate_all(metrics, COST_METRICS, "metrics")
    validate_all(group_by, COST_GROUP_DIMENSIONS, "group_by dimensions")

    request: dict[str, Any] = {
        "TimePeriod": {"Start": start, "End": end},
        "Granularity": granularity,
        "Metrics": metrics,
        "GroupBy": [{"Type": "DIMENSION", "Key": item} for item in group_by],
    }
    filter_expression = parse_filter(filter_json)

    if filter_expression:
        request["Filter"] = filter_expression

    return collect_pages(
        cost_explorer,
        "get_cost_and_usage",
        "ResultsByTime",
        config.max_pages,
        **request,
    )


def create_billing_read_tools(config: AwsToolConfig) -> list[Any]:
    """Create tools that read AWS billing and Cost Explorer data."""
    session = create_boto3_session(config)
    cost_explorer = session.client("ce", region_name=config.region)

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
            return json_dumps(
                fetch_cost_and_usage(
                    cost_explorer=cost_explorer,
                    config=config,
                    start=start,
                    end=end,
                    granularity=granularity,
                    metrics_csv=metrics_csv,
                    group_by_csv=group_by_csv,
                    filter_json=filter_json,
                )
            )
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

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
            validate_all([metric], FORECAST_METRICS, "forecast metric")

            return json_dumps(
                cost_explorer.get_cost_forecast(
                    TimePeriod={"Start": start, "End": end},
                    Metric=metric,
                    Granularity=granularity,
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [get_cost_and_usage, get_cost_forecast]
