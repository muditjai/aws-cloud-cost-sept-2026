from __future__ import annotations

from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import AwsToolConfig, client_error_message, create_boto3_session, json_dumps
from .service_costs import cloudwatch_metric, fetch_resource_level_costs, fetch_service_component_costs


CLOUDFRONT_SERVICE = "Amazon CloudFront"
CLOUDFRONT_METRICS = {
    "Requests": ["Sum"],
    "BytesDownloaded": ["Sum"],
    "BytesUploaded": ["Sum"],
    "TotalErrorRate": ["Average"],
    "CacheHitRate": ["Average"],
}


def fetch_cloudfront_inventory(config: AwsToolConfig) -> dict[str, Any]:
    """Inventory CloudFront distributions and cost-relevant configuration."""
    client = create_boto3_session(config).client("cloudfront", region_name="us-east-1")
    distributions = []
    for page in client.get_paginator("list_distributions").paginate():
        for summary in page.get("DistributionList", {}).get("Items", []):
            distribution_id = summary["Id"]
            configuration = client.get_distribution_config(Id=distribution_id)["DistributionConfig"]
            distributions.append(
                {
                    "id": distribution_id,
                    "arn": summary.get("ARN"),
                    "status": summary.get("Status"),
                    "enabled": summary.get("Enabled"),
                    "domain_name": summary.get("DomainName"),
                    "aliases": summary.get("Aliases", {}).get("Items", []),
                    "price_class": summary.get("PriceClass"),
                    "http_version": summary.get("HttpVersion"),
                    "ipv6_enabled": summary.get("IsIPV6Enabled"),
                    "origin_count": summary.get("Origins", {}).get("Quantity"),
                    "origins": [
                        {
                            "id": origin.get("Id"),
                            "domain_name": origin.get("DomainName"),
                        }
                        for origin in summary.get("Origins", {}).get("Items", [])
                    ],
                    "default_cache_behavior": {
                        "target_origin_id": configuration.get("DefaultCacheBehavior", {}).get(
                            "TargetOriginId"
                        ),
                        "viewer_protocol_policy": configuration.get(
                            "DefaultCacheBehavior", {}
                        ).get("ViewerProtocolPolicy"),
                        "cache_policy_id": configuration.get("DefaultCacheBehavior", {}).get(
                            "CachePolicyId"
                        ),
                        "compress": configuration.get("DefaultCacheBehavior", {}).get("Compress"),
                    },
                    "additional_cache_behaviors": configuration.get("CacheBehaviors", {}).get(
                        "Quantity", 0
                    ),
                    "logging_enabled": configuration.get("Logging", {}).get("Enabled"),
                }
            )
    return {"distributions": distributions}


def fetch_cloudfront_utilization(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Return request, transfer, cache, and error metrics by distribution."""
    inventory = fetch_cloudfront_inventory(config)
    cloudwatch = create_boto3_session(config).client("cloudwatch", region_name="us-east-1")
    distributions = []
    for distribution in inventory["distributions"]:
        metrics = {}
        dimensions = [
            {"Name": "DistributionId", "Value": distribution["id"]},
            {"Name": "Region", "Value": "Global"},
        ]
        for metric_name, statistics in CLOUDFRONT_METRICS.items():
            try:
                metrics[metric_name] = cloudwatch_metric(
                    cloudwatch,
                    "AWS/CloudFront",
                    metric_name,
                    dimensions,
                    start_date,
                    end_date,
                    statistics,
                )
            except (BotoCoreError, ClientError) as error:
                metrics[metric_name] = {"error": client_error_message(error)}
        distributions.append(
            {
                "id": distribution["id"],
                "aliases": distribution["aliases"],
                "enabled": distribution["enabled"],
                "price_class": distribution["price_class"],
                "metrics": metrics,
            }
        )
    return {"distributions": distributions}


def fetch_cloudfront_cost_attribution(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Estimate request and transfer cost by distribution using CloudWatch shares."""
    costs = fetch_service_component_costs(
        config,
        CLOUDFRONT_SERVICE,
        start_date,
        end_date,
    )
    utilization = fetch_cloudfront_utilization(config, start_date, end_date)
    request_cost = sum(
        row["amount"]
        for row in costs["by_usage_type_and_operation"]
        if "Request" in row.get("keys", [""])[0]
    )
    transfer_cost = sum(
        row["amount"]
        for row in costs["by_usage_type_and_operation"]
        if "Byte" in row.get("keys", [""])[0]
    )
    total_requests = sum(
        float(item["metrics"].get("Requests", {}).get("sum", 0))
        for item in utilization["distributions"]
    )
    total_bytes = sum(
        float(item["metrics"].get("BytesDownloaded", {}).get("sum", 0))
        for item in utilization["distributions"]
    )
    estimates = []
    for item in utilization["distributions"]:
        requests = float(item["metrics"].get("Requests", {}).get("sum", 0))
        downloaded = float(item["metrics"].get("BytesDownloaded", {}).get("sum", 0))
        estimated_request_cost = request_cost * requests / total_requests if total_requests else 0
        estimated_transfer_cost = transfer_cost * downloaded / total_bytes if total_bytes else 0
        estimates.append(
            {
                **item,
                "estimated_request_cost": estimated_request_cost,
                "estimated_transfer_cost": estimated_transfer_cost,
                "estimated_variable_cost": estimated_request_cost + estimated_transfer_cost,
            }
        )
    estimates.sort(key=lambda item: item["estimated_variable_cost"], reverse=True)
    return {
        "exact_cost_pools": {"requests": request_cost, "byte_based": transfer_cost},
        "per_distribution_estimates": estimates,
        "unallocated_cost": costs["total"] - request_cost - transfer_cost,
        "limitations": [
            "Request costs are allocated by each distribution's request share across all edge regions and request classes.",
            "Byte-based costs are allocated by BytesDownloaded share and are not invoice-level resource attribution.",
            "Resource-level Cost Explorer data is required for exact per-distribution charges.",
        ],
    }


def create_cloudfront_analysis_tools(config: AwsToolConfig) -> list[Any]:
    """Create CloudFront-specific cost, inventory, utilization, and attribution tools."""

    @tool
    def get_cloudfront_component_costs(start_date: str, end_date: str) -> str:
        """Return exact CloudFront costs by usage type, operation, and region."""
        try:
            return json_dumps(
                fetch_service_component_costs(
                    config, CLOUDFRONT_SERVICE, start_date, end_date
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_cloudfront_resource_costs(start_date: str, end_date: str) -> str:
        """Return opt-in CloudFront costs by resource ID for the available window."""
        try:
            return json_dumps(
                fetch_resource_level_costs(
                    config, CLOUDFRONT_SERVICE, start_date, end_date
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_cloudfront_inventory() -> str:
        """List CloudFront distributions and cost-relevant configuration."""
        try:
            return json_dumps(fetch_cloudfront_inventory(config))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_cloudfront_utilization(start_date: str, end_date: str) -> str:
        """Return request, transfer, cache-hit, and error metrics by distribution."""
        try:
            return json_dumps(fetch_cloudfront_utilization(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_cloudfront_cost_attribution(start_date: str, end_date: str) -> str:
        """Estimate request and transfer dollars by CloudFront distribution."""
        try:
            return json_dumps(fetch_cloudfront_cost_attribution(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [
        get_cloudfront_component_costs,
        get_cloudfront_resource_costs,
        get_cloudfront_inventory,
        get_cloudfront_utilization,
        get_cloudfront_cost_attribution,
    ]
