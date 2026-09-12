from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from botocore.exceptions import ClientError

from ..bill_read.aws_billing import fetch_cost_and_usage
from ..shared import (
    AwsToolConfig,
    client_error_message,
    collect_pages,
    create_boto3_session,
    service_filter,
    summarize_cost_groups,
)


def fetch_service_component_costs(
    config: AwsToolConfig,
    service: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Return exact service costs by usage type, operation, and region."""
    filter_json = json.dumps(service_filter(service))
    usage_operation = fetch_cost_and_usage(
        config,
        start_date,
        end_date,
        "USAGE_TYPE,OPERATION",
        filter_json,
    )
    region_data = fetch_cost_and_usage(config, start_date, end_date, "REGION", filter_json)
    components = summarize_cost_groups(usage_operation, "UnblendedCost")
    regions = summarize_cost_groups(region_data, "UnblendedCost")
    return {
        "service": service,
        "start_date": start_date,
        "end_date": end_date,
        "total": sum(row["amount"] for row in components),
        "unit": "USD",
        "by_usage_type_and_operation": components,
        "by_region": regions,
    }


def positive_cost_regions(costs: dict[str, Any]) -> list[str]:
    """Return concrete AWS regions with positive service cost."""
    return [
        row["key"]
        for row in costs.get("by_region", [])
        if row["amount"] > 0 and row["key"] not in {"global", "NoRegion"}
    ]


def fetch_resource_level_costs(
    config: AwsToolConfig,
    service: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Read opt-in daily resource costs for the available 14-day window."""
    requested_start = date.fromisoformat(start_date)
    requested_end = date.fromisoformat(end_date)
    resource_start = max(requested_start, date.today() - timedelta(days=14))
    if resource_start >= requested_end:
        return {
            "available": False,
            "reason": "The requested period is outside the 14-day resource-level data window.",
        }

    client = create_boto3_session(config).client("ce", region_name="us-east-1")
    try:
        data = collect_pages(
            client,
            "get_cost_and_usage_with_resources",
            "ResultsByTime",
            TimePeriod={"Start": resource_start.isoformat(), "End": end_date},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            Filter=service_filter(service),
            GroupBy=[
                {"Type": "DIMENSION", "Key": "RESOURCE_ID"},
                {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
            ],
        )
    except ClientError as error:
        details = error.response.get("Error", {})
        if details.get("Code") == "AccessDeniedException" and "opt-in" in str(error).lower():
            return {
                "available": False,
                "start_date": resource_start.isoformat(),
                "end_date": end_date,
                "reason": client_error_message(error),
            }
        raise

    rows = summarize_cost_groups(data, "UnblendedCost")
    return {
        "available": True,
        "start_date": resource_start.isoformat(),
        "end_date": end_date,
        "window_was_clamped": resource_start != requested_start,
        "resources": [row for row in rows if row["amount"] != 0],
    }


def cloudwatch_metric(
    cloudwatch: Any,
    namespace: str,
    metric_name: str,
    dimensions: list[dict[str, str]],
    start_date: str,
    end_date: str,
    statistics: list[str],
) -> dict[str, Any]:
    """Summarize daily CloudWatch metric points for a billing-period analysis."""
    start = datetime.combine(date.fromisoformat(start_date), time.min, timezone.utc)
    end = datetime.combine(date.fromisoformat(end_date), time.min, timezone.utc)
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start,
        EndTime=end,
        Period=86400,
        Statistics=statistics,
    )
    datapoints = response.get("Datapoints", [])
    summary: dict[str, Any] = {
        "datapoint_count": len(datapoints),
        "unit": next((point.get("Unit") for point in datapoints if point.get("Unit")), None),
    }
    if "Sum" in statistics:
        summary["sum"] = sum(float(point.get("Sum", 0)) for point in datapoints)
    if "Average" in statistics:
        averages = [float(point["Average"]) for point in datapoints if "Average" in point]
        summary["average"] = sum(averages) / len(averages) if averages else None
    if "Maximum" in statistics:
        maximums = [float(point["Maximum"]) for point in datapoints if "Maximum" in point]
        summary["maximum"] = max(maximums) if maximums else None
    return summary
