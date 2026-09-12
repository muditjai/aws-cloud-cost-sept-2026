from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..bill_read.aws_billing import fetch_cost_and_usage
from ..shared import (
    AwsToolConfig,
    client_error_message,
    collect_pages,
    create_boto3_session,
    json_dumps,
    service_filter,
    strip_metadata,
    summarize_cost_groups,
)


ELB_SERVICE = "Amazon Elastic Load Balancing"
V2_METRICS = {
    "application": ("AWS/ApplicationELB", ("ProcessedBytes", "RequestCount", "ConsumedLCUs")),
    "network": ("AWS/NetworkELB", ("ProcessedBytes", "ActiveFlowCount", "ConsumedLCUs")),
    "gateway": ("AWS/GatewayELB", ("ProcessedBytes", "ActiveFlowCount", "ConsumedLCUs")),
}


def _elb_filter() -> str:
    return json.dumps(service_filter(ELB_SERVICE))


def _positive_cost_regions(config: AwsToolConfig, start_date: str, end_date: str) -> list[str]:
    data = fetch_cost_and_usage(config, start_date, end_date, "REGION", _elb_filter())
    return [
        row["key"]
        for row in summarize_cost_groups(data, "UnblendedCost")
        if row["amount"] > 0 and row["key"] not in {"global", "NoRegion"}
    ]


def fetch_elb_component_costs(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Return exact Cost Explorer ELB totals by billable component and region."""
    usage_operation = fetch_cost_and_usage(
        config,
        start_date,
        end_date,
        "USAGE_TYPE,OPERATION",
        _elb_filter(),
    )
    regions = fetch_cost_and_usage(config, start_date, end_date, "REGION", _elb_filter())
    components = summarize_cost_groups(usage_operation, "UnblendedCost")
    by_region = summarize_cost_groups(regions, "UnblendedCost")
    return {
        "service": ELB_SERVICE,
        "start_date": start_date,
        "end_date": end_date,
        "total": sum(row["amount"] for row in components),
        "unit": "USD",
        "by_usage_type_and_operation": components,
        "by_region": by_region,
    }


def fetch_elb_resource_costs(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Read opt-in daily ELB resource costs for the portion available in Cost Explorer."""
    requested_start = date.fromisoformat(start_date)
    requested_end = date.fromisoformat(end_date)
    earliest_available = date.today() - timedelta(days=14)
    resource_start = max(requested_start, earliest_available)

    if resource_start >= requested_end:
        return {
            "available": False,
            "reason": "The requested period is outside the 14-day resource-level data window.",
        }

    request = {
        "TimePeriod": {"Start": resource_start.isoformat(), "End": end_date},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "Filter": service_filter(ELB_SERVICE),
        "GroupBy": [
            {"Type": "DIMENSION", "Key": "RESOURCE_ID"},
            {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
        ],
    }
    client = create_boto3_session(config).client("ce", region_name="us-east-1")
    try:
        data = collect_pages(
            client,
            "get_cost_and_usage_with_resources",
            "ResultsByTime",
            **request,
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


def _v2_inventory(client: Any) -> list[dict[str, Any]]:
    target_groups: dict[str, list[dict[str, Any]]] = {}
    for page in client.get_paginator("describe_target_groups").paginate():
        for group in page.get("TargetGroups", []):
            targets: list[dict[str, Any]] = []
            try:
                health = client.describe_target_health(TargetGroupArn=group["TargetGroupArn"])
                targets = [
                    {
                        "id": item["Target"]["Id"],
                        "port": item["Target"].get("Port"),
                        "availability_zone": item["Target"].get("AvailabilityZone"),
                        "state": item["TargetHealth"].get("State"),
                    }
                    for item in health.get("TargetHealthDescriptions", [])
                ]
            except (BotoCoreError, ClientError) as error:
                targets = [{"error": client_error_message(error)}]

            summary = {
                "name": group.get("TargetGroupName"),
                "arn": group.get("TargetGroupArn"),
                "target_type": group.get("TargetType"),
                "protocol": group.get("Protocol"),
                "port": group.get("Port"),
                "targets": targets,
            }
            for load_balancer_arn in group.get("LoadBalancerArns", []):
                target_groups.setdefault(load_balancer_arn, []).append(summary)

    load_balancers: list[dict[str, Any]] = []
    for page in client.get_paginator("describe_load_balancers").paginate():
        for load_balancer in page.get("LoadBalancers", []):
            arn = load_balancer["LoadBalancerArn"]
            listeners = list(
                client.get_paginator("describe_listeners").paginate(LoadBalancerArn=arn)
            )
            load_balancers.append(
                {
                    "name": load_balancer.get("LoadBalancerName"),
                    "arn": arn,
                    "type": load_balancer.get("Type"),
                    "scheme": load_balancer.get("Scheme"),
                    "state": load_balancer.get("State", {}).get("Code"),
                    "created_time": load_balancer.get("CreatedTime"),
                    "vpc_id": load_balancer.get("VpcId"),
                    "availability_zones": [
                        zone.get("ZoneName") for zone in load_balancer.get("AvailabilityZones", [])
                    ],
                    "listener_count": sum(len(page.get("Listeners", [])) for page in listeners),
                    "target_groups": target_groups.get(arn, []),
                }
            )
    return load_balancers


def _classic_inventory(client: Any) -> list[dict[str, Any]]:
    load_balancers: list[dict[str, Any]] = []
    for page in client.get_paginator("describe_load_balancers").paginate():
        for load_balancer in page.get("LoadBalancerDescriptions", []):
            load_balancers.append(
                {
                    "name": load_balancer.get("LoadBalancerName"),
                    "type": "classic",
                    "scheme": load_balancer.get("Scheme"),
                    "created_time": load_balancer.get("CreatedTime"),
                    "vpc_id": load_balancer.get("VPCId"),
                    "availability_zones": load_balancer.get("AvailabilityZones", []),
                    "listener_count": len(load_balancer.get("ListenerDescriptions", [])),
                    "targets": [item.get("InstanceId") for item in load_balancer.get("Instances", [])],
                }
            )
    return load_balancers


def fetch_elb_inventory(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Inventory load balancers and registered targets in regions with ELB cost."""
    session = create_boto3_session(config)
    result: dict[str, Any] = {"regions": {}, "errors": {}}
    for region in _positive_cost_regions(config, start_date, end_date):
        try:
            result["regions"][region] = {
                "v2": _v2_inventory(session.client("elbv2", region_name=region)),
                "classic": _classic_inventory(session.client("elb", region_name=region)),
            }
        except (BotoCoreError, ClientError) as error:
            result["errors"][region] = client_error_message(error)
    return result


def _metric_summary(
    cloudwatch: Any,
    namespace: str,
    metric_name: str,
    dimension_name: str,
    dimension_value: str,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    is_lcu = metric_name == "ConsumedLCUs"
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=[{"Name": dimension_name, "Value": dimension_value}],
        StartTime=start,
        EndTime=end,
        Period=3600 if is_lcu else 86400,
        Statistics=["Sum"],
    )
    datapoints = response.get("Datapoints", [])
    value = sum(float(point.get("Sum", 0)) for point in datapoints)
    return {
        "value": value,
        "unit": "LCU metric units" if is_lcu else response.get("Label", metric_name),
        "datapoint_count": len(datapoints),
    }


def fetch_elb_utilization(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Return per-load-balancer traffic and LCU metrics for relative cost attribution."""
    inventory = fetch_elb_inventory(config, start_date, end_date)
    start = datetime.combine(date.fromisoformat(start_date), time.min, timezone.utc)
    end = datetime.combine(date.fromisoformat(end_date), time.min, timezone.utc)
    session = create_boto3_session(config)
    output: dict[str, Any] = {"regions": {}, "errors": dict(inventory.get("errors", {}))}

    for region, regional_inventory in inventory.get("regions", {}).items():
        cloudwatch = session.client("cloudwatch", region_name=region)
        regional_metrics: list[dict[str, Any]] = []
        for load_balancer in regional_inventory.get("v2", []):
            load_balancer_type = load_balancer.get("type")
            metric_config = V2_METRICS.get(load_balancer_type)
            if not metric_config:
                continue
            namespace, metric_names = metric_config
            dimension_value = load_balancer["arn"].split("loadbalancer/", 1)[-1]
            metrics: dict[str, Any] = {}
            for metric_name in metric_names:
                try:
                    metrics[metric_name] = _metric_summary(
                        cloudwatch,
                        namespace,
                        metric_name,
                        "LoadBalancer",
                        dimension_value,
                        start,
                        end,
                    )
                except (BotoCoreError, ClientError) as error:
                    metrics[metric_name] = {"error": client_error_message(error)}
            regional_metrics.append(
                {
                    "name": load_balancer.get("name"),
                    "arn": load_balancer.get("arn"),
                    "type": load_balancer_type,
                    "metrics": metrics,
                }
            )

        for load_balancer in regional_inventory.get("classic", []):
            metrics = {}
            for metric_name in ("ProcessedBytes", "RequestCount"):
                try:
                    metrics[metric_name] = _metric_summary(
                        cloudwatch,
                        "AWS/ELB",
                        metric_name,
                        "LoadBalancerName",
                        load_balancer["name"],
                        start,
                        end,
                    )
                except (BotoCoreError, ClientError) as error:
                    metrics[metric_name] = {"error": client_error_message(error)}
            regional_metrics.append({**load_balancer, "metrics": metrics})
        output["regions"][region] = regional_metrics

    return strip_metadata(output)


def create_elb_analysis_tools(config: AwsToolConfig) -> list[Any]:
    """Create ELB-specific cost, inventory, and utilization tools."""

    @tool
    def get_elb_component_costs(start_date: str, end_date: str) -> str:
        """Return exact ELB cost by usage type, operation, and region."""
        try:
            return json_dumps(fetch_elb_component_costs(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_elb_resource_costs(start_date: str, end_date: str) -> str:
        """Return opt-in ELB cost by resource ID for the available 14-day window."""
        try:
            return json_dumps(fetch_elb_resource_costs(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_elb_inventory(start_date: str, end_date: str) -> str:
        """List load balancers and targets in regions that incurred ELB cost."""
        try:
            return json_dumps(fetch_elb_inventory(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_elb_utilization(start_date: str, end_date: str) -> str:
        """Return traffic and LCU billing metrics by load balancer."""
        try:
            return json_dumps(fetch_elb_utilization(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [
        get_elb_component_costs,
        get_elb_resource_costs,
        get_elb_inventory,
        get_elb_utilization,
    ]
