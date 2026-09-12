from __future__ import annotations

import json
from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..bill_read.aws_billing import fetch_cost_and_usage
from ..shared import (
    COST_METRICS,
    AwsToolConfig,
    client_error_message,
    create_boto3_session,
    csv_values,
    json_dumps,
    service_filter,
    summarize_cost_groups,
    validate_all,
)


TECHNOLOGY_SERVICE_HINTS: dict[str, list[str]] = {
    "cdn": ["Amazon CloudFront"],
    "cloudfront": ["Amazon CloudFront"],
    "ec2": ["Amazon Elastic Compute Cloud - Compute", "EC2 - Other"],
    "elb": ["Amazon Elastic Load Balancing"],
    "load-balancer": ["Amazon Elastic Load Balancing"],
    "s3": ["Amazon Simple Storage Service"],
    "vpc": ["Amazon Virtual Private Cloud", "EC2 - Other"],
}


def create_per_technology_analysis_tools(config: AwsToolConfig) -> list[Any]:
    """Create tools that analyze top service and SKU cost drivers."""
    session = create_boto3_session(config)
    cost_explorer = session.client("ce", region_name=config.region)

    @tool
    def get_known_technology_service_hints() -> str:
        """Return known mappings from technology names to AWS Cost Explorer SERVICE values."""
        return json_dumps(TECHNOLOGY_SERVICE_HINTS)

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
            validate_all([metric], COST_METRICS, "metric")
            raw = fetch_cost_and_usage(
                cost_explorer=cost_explorer,
                config=config,
                start=start,
                end=end,
                granularity=granularity,
                metrics_csv=metric,
                group_by_csv=group_by_csv,
                filter_json=filter_json,
            )
            drivers = summarize_cost_groups(raw, metric)

            return json_dumps(
                {
                    "metric": metric,
                    "group_by": csv_values(group_by_csv),
                    "top_drivers": drivers[:limit],
                    "driver_count": len(drivers),
                    "source": raw,
                }
            )
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

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
            validate_all([metric], COST_METRICS, "metric")
            raw = fetch_cost_and_usage(
                cost_explorer=cost_explorer,
                config=config,
                start=start,
                end=end,
                granularity=granularity,
                metrics_csv=metric,
                group_by_csv=group_by_csv,
                filter_json=json.dumps(service_filter(service, filter_json)),
            )
            drivers = summarize_cost_groups(raw, metric)

            return json_dumps(
                {
                    "service": service,
                    "metric": metric,
                    "group_by": csv_values(group_by_csv),
                    "top_breakdown_rows": drivers[:limit],
                    "breakdown_row_count": len(drivers),
                    "source": raw,
                }
            )
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [
        get_known_technology_service_hints,
        get_top_cost_drivers,
        get_service_cost_breakdown,
    ]
