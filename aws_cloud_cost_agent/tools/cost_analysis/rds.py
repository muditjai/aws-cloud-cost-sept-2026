from __future__ import annotations

from typing import Any

from ..function_tool import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import AwsToolConfig, client_error_message, create_boto3_session, json_dumps
from .service_costs import (
    cloudwatch_metric,
    fetch_resource_level_costs,
    fetch_service_component_costs,
    positive_cost_regions,
)


RDS_SERVICE = "Amazon Relational Database Service"
RDS_INSTANCE_METRICS = (
    "CPUUtilization",
    "DatabaseConnections",
    "FreeableMemory",
    "ServerlessDatabaseCapacity",
)


def fetch_rds_inventory(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Inventory RDS instances and clusters in regions with RDS spend."""
    costs = fetch_service_component_costs(config, RDS_SERVICE, start_date, end_date)
    session = create_boto3_session(config)
    output: dict[str, Any] = {"regions": {}, "errors": {}}
    for region in positive_cost_regions(costs):
        try:
            client = session.client("rds", region_name=region)
            instances = []
            for page in client.get_paginator("describe_db_instances").paginate():
                for instance in page.get("DBInstances", []):
                    instances.append(
                        {
                            "identifier": instance.get("DBInstanceIdentifier"),
                            "arn": instance.get("DBInstanceArn"),
                            "status": instance.get("DBInstanceStatus"),
                            "engine": instance.get("Engine"),
                            "engine_version": instance.get("EngineVersion"),
                            "instance_class": instance.get("DBInstanceClass"),
                            "cluster_identifier": instance.get("DBClusterIdentifier"),
                            "availability_zone": instance.get("AvailabilityZone"),
                            "multi_az": instance.get("MultiAZ"),
                            "storage_type": instance.get("StorageType"),
                            "allocated_storage_gib": instance.get("AllocatedStorage"),
                            "max_allocated_storage_gib": instance.get("MaxAllocatedStorage"),
                            "iops": instance.get("Iops"),
                            "storage_throughput": instance.get("StorageThroughput"),
                            "created_time": instance.get("InstanceCreateTime"),
                            "performance_insights": instance.get("PerformanceInsightsEnabled"),
                        }
                    )

            clusters = []
            for page in client.get_paginator("describe_db_clusters").paginate():
                for cluster in page.get("DBClusters", []):
                    clusters.append(
                        {
                            "identifier": cluster.get("DBClusterIdentifier"),
                            "arn": cluster.get("DBClusterArn"),
                            "status": cluster.get("Status"),
                            "engine": cluster.get("Engine"),
                            "engine_version": cluster.get("EngineVersion"),
                            "engine_mode": cluster.get("EngineMode"),
                            "storage_type": cluster.get("StorageType"),
                            "backup_retention_days": cluster.get("BackupRetentionPeriod"),
                            "serverless_v2_scaling": cluster.get("ServerlessV2ScalingConfiguration"),
                            "members": [
                                {
                                    "identifier": member.get("DBInstanceIdentifier"),
                                    "writer": member.get("IsClusterWriter"),
                                }
                                for member in cluster.get("DBClusterMembers", [])
                            ],
                        }
                    )
            output["regions"][region] = {"instances": instances, "clusters": clusters}
        except (BotoCoreError, ClientError) as error:
            output["errors"][region] = client_error_message(error)
    return output


def fetch_rds_utilization(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Return utilization metrics for each current RDS instance."""
    inventory = fetch_rds_inventory(config, start_date, end_date)
    session = create_boto3_session(config)
    output: dict[str, Any] = {"regions": {}, "errors": dict(inventory.get("errors", {}))}
    for region, regional_inventory in inventory.get("regions", {}).items():
        cloudwatch = session.client("cloudwatch", region_name=region)
        instances = []
        for instance in regional_inventory.get("instances", []):
            metrics = {}
            for metric_name in RDS_INSTANCE_METRICS:
                try:
                    metrics[metric_name] = cloudwatch_metric(
                        cloudwatch,
                        "AWS/RDS",
                        metric_name,
                        [{"Name": "DBInstanceIdentifier", "Value": instance["identifier"]}],
                        start_date,
                        end_date,
                        ["Average", "Maximum"],
                    )
                except (BotoCoreError, ClientError) as error:
                    metrics[metric_name] = {"error": client_error_message(error)}
            instances.append(
                {
                    "identifier": instance.get("identifier"),
                    "instance_class": instance.get("instance_class"),
                    "engine": instance.get("engine"),
                    "metrics": metrics,
                }
            )
        output["regions"][region] = instances
    return output


def fetch_rds_cost_attribution(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Estimate compute and GP3 cost by current RDS instance using billing-aligned drivers."""
    costs = fetch_service_component_costs(config, RDS_SERVICE, start_date, end_date)
    inventory = fetch_rds_inventory(config, start_date, end_date)
    utilization = fetch_rds_utilization(config, start_date, end_date)
    class_costs: dict[str, float] = {}
    serverless_cost = 0.0
    gp3_cost = 0.0
    for row in costs["by_usage_type_and_operation"]:
        usage_type = row.get("keys", [""])[0]
        if usage_type.startswith("InstanceUsage:db."):
            class_costs[usage_type.removeprefix("InstanceUsage:")] = row["amount"]
        elif usage_type == "Aurora:ServerlessV2Usage":
            serverless_cost += row["amount"]
        elif usage_type == "RDS:GP3-Storage":
            gp3_cost += row["amount"]

    instances = [
        {"region": region, **instance}
        for region, regional_inventory in inventory.get("regions", {}).items()
        for instance in regional_inventory.get("instances", [])
    ]
    metrics = {
        item["identifier"]: item.get("metrics", {})
        for regional_metrics in utilization.get("regions", {}).values()
        for item in regional_metrics
    }
    class_counts: dict[str, int] = {}
    for instance in instances:
        instance_class = instance.get("instance_class")
        class_counts[instance_class] = class_counts.get(instance_class, 0) + 1
    total_gp3_gib = sum(
        float(instance.get("allocated_storage_gib") or 0)
        for instance in instances
        if instance.get("storage_type") == "gp3"
    )
    total_serverless_acu = sum(
        float(
            metrics.get(instance["identifier"], {})
            .get("ServerlessDatabaseCapacity", {})
            .get("average")
            or 0
        )
        for instance in instances
        if instance.get("instance_class") == "db.serverless"
    )

    estimates = []
    for instance in instances:
        identifier = instance["identifier"]
        instance_class = instance.get("instance_class")
        instance_metrics = metrics.get(identifier, {})
        compute_cost = 0.0
        if instance_class == "db.serverless":
            average_acu = float(
                instance_metrics.get("ServerlessDatabaseCapacity", {}).get("average") or 0
            )
            if total_serverless_acu:
                compute_cost = serverless_cost * average_acu / total_serverless_acu
        elif class_counts.get(instance_class):
            compute_cost = class_costs.get(instance_class, 0) / class_counts[instance_class]

        storage_gib = float(instance.get("allocated_storage_gib") or 0)
        storage_cost = (
            gp3_cost * storage_gib / total_gp3_gib
            if instance.get("storage_type") == "gp3" and total_gp3_gib
            else 0
        )
        estimates.append(
            {
                "identifier": identifier,
                "region": instance.get("region"),
                "engine": instance.get("engine"),
                "instance_class": instance_class,
                "estimated_compute_cost": compute_cost,
                "estimated_gp3_storage_cost": storage_cost,
                "estimated_attributed_cost": compute_cost + storage_cost,
                "cpu_average_percent": instance_metrics.get("CPUUtilization", {}).get("average"),
                "cpu_maximum_percent": instance_metrics.get("CPUUtilization", {}).get("maximum"),
                "database_connections_average": instance_metrics.get(
                    "DatabaseConnections", {}
                ).get("average"),
                "serverless_capacity_average_acu": instance_metrics.get(
                    "ServerlessDatabaseCapacity", {}
                ).get("average"),
            }
        )
    estimates.sort(key=lambda item: item["estimated_attributed_cost"], reverse=True)
    allocatable_cost = serverless_cost + gp3_cost + sum(class_costs.values())
    return {
        "exact_cost_pools": {
            "aurora_serverless_v2": serverless_cost,
            "gp3_storage": gp3_cost,
            "provisioned_instance_classes": class_costs,
        },
        "per_instance_estimates": estimates,
        "attributed_cost": sum(item["estimated_attributed_cost"] for item in estimates),
        "unallocated_cost": costs["total"] - allocatable_cost,
        "limitations": [
            "Provisioned class cost is divided across current matching instances because resource-level Cost Explorer is disabled.",
            "Aurora Serverless v2 cost is allocated by average ServerlessDatabaseCapacity across the common time window.",
            "GP3 storage cost is allocated by current provisioned GiB; backup, Aurora storage, and I/O costs remain unallocated.",
        ],
        "errors": {**inventory.get("errors", {}), **utilization.get("errors", {})},
    }


def create_rds_analysis_tools(config: AwsToolConfig) -> list[Any]:
    """Create RDS-specific cost, inventory, and utilization tools."""

    @tool
    def get_rds_component_costs(start_date: str, end_date: str) -> str:
        """Return exact RDS costs by usage type, operation, and region."""
        try:
            return json_dumps(fetch_service_component_costs(config, RDS_SERVICE, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_rds_resource_costs(start_date: str, end_date: str) -> str:
        """Return opt-in RDS cost by resource ID for the available 14-day window."""
        try:
            return json_dumps(
                fetch_resource_level_costs(config, RDS_SERVICE, start_date, end_date)
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_rds_inventory(start_date: str, end_date: str) -> str:
        """List RDS instances, clusters, sizing, storage, and serverless settings."""
        try:
            return json_dumps(fetch_rds_inventory(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_rds_utilization(start_date: str, end_date: str) -> str:
        """Return CPU, connections, memory, and serverless capacity by DB instance."""
        try:
            return json_dumps(fetch_rds_utilization(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_rds_cost_attribution(start_date: str, end_date: str) -> str:
        """Estimate compute and GP3 storage dollars by current RDS instance."""
        try:
            return json_dumps(fetch_rds_cost_attribution(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [
        get_rds_component_costs,
        get_rds_resource_costs,
        get_rds_inventory,
        get_rds_utilization,
        get_rds_cost_attribution,
    ]
