"""Read-only billing, load balancer, DNS, CDN, and CloudWatch collection."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
import re
from typing import Any

import boto3
from botocore.config import Config
from botocore.paginate import Paginator

from .common import Json, attempt, normalize_host, utc_day

TRANSFER_PATTERN = re.compile(
    r"DataTransfer|AWS-(?:In|Out)-Bytes|Bytes-(?:Internet|AWS)|CloudFront-.*-Bytes|DataXfer|-ABytes-")


class AwsCollector:
    def __init__(self, environment: dict[str, str], start: date, end: date,
                 regions: list[str], issues: list[str]) -> None:
        self.start, self.end, self.regions, self.issues = start, end, regions, issues
        self.region = environment.get("AWS_REGION", environment.get("AWS_DEFAULT_REGION", "us-east-1"))
        credentials = {}
        for source, target in [("AWS_ACCESS_KEY_ID", "aws_access_key_id"),
                               ("AWS_SECRET_ACCESS_KEY", "aws_secret_access_key"),
                               ("AWS_SESSION_TOKEN", "aws_session_token")]:
            if environment.get(source):
                credentials[target] = environment[source]
        if not credentials and environment.get("AWS_PROFILE"):
            credentials["profile_name"] = environment["AWS_PROFILE"]
        self.session = boto3.Session(region_name=self.region, **credentials)
        self.config = Config(connect_timeout=5, read_timeout=25,
                             retries={"mode": "standard", "total_max_attempts": 3})
        self.clients: dict[tuple[str, str], Any] = {}

    def client(self, service: str, region: str = "") -> Any:
        identity = (service, region or self.region)
        if identity not in self.clients:
            self.clients[identity] = self.session.client(service, region_name=identity[1], config=self.config)
        return self.clients[identity]

    def pages(self, service: str, operation: str, key: str, region: str = "", **kwargs: Any) -> list[Json]:
        return [item for page in self.client(service, region).get_paginator(operation).paginate(**kwargs)
                for item in page.get(key, [])]

    def collect(self) -> Json:
        identity = attempt(self.issues, "AWS caller identity",
                           lambda: self.client("sts").get_caller_identity(), {})
        if not identity:
            return {"status": "unavailable", "load_balancers": [], "billing": []}
        account = identity["Account"]
        billing = attempt(self.issues, "Cost Explorer", lambda: self.billing(account), [])
        regions = self.regions or attempt(self.issues, "Enabled region discovery", lambda: [
            item["RegionName"] for item in self.client("ec2").describe_regions()["Regions"]], [self.region])
        balancers: list[Json] = []
        for region in regions:
            modern = attempt(self.issues, f"ELBv2 inventory {region}",
                             lambda: self.pages("elbv2", "describe_load_balancers", "LoadBalancers", region), [])
            classic = attempt(self.issues, f"Classic ELB inventory {region}",
                              lambda: self.pages("elb", "describe_load_balancers", "LoadBalancerDescriptions", region), [])
            for item in modern + classic:
                balancer = self.describe_balancer(item, region)
                print(f"  AWS: {balancer['name']} ({region}, {balancer['type']})", flush=True)
                balancers.append(balancer)
        dns = attempt(self.issues, "Route 53 discovery", self.dns_records, [])
        cdns = attempt(self.issues, "CloudFront discovery", self.distributions, [])
        link_domains(balancers, dns, cdns)
        for balancer in balancers:
            balancer["metrics"] = attempt(self.issues, f"CloudWatch {balancer['name']}",
                                           lambda: self.metrics(balancer), {})
        return {"status": "collected", "account": account, "regions": regions, "billing": billing,
                "load_balancers": balancers, "dns": dns, "cloudfront": cdns}

    def billing(self, account: str) -> list[Json]:
        # Capture the current UTC date at execution; Cost Explorer End is exclusive.
        from datetime import datetime, timezone
        if self.end > datetime.now(timezone.utc).date():
            raise ValueError("Billing end date cannot be in the future")
        rows = []
        client = self.client("ce", "us-east-1")
        # Some botocore releases omit CE pagination metadata even though the API paginates.
        paginator = (client.get_paginator("get_cost_and_usage") if client.can_paginate("get_cost_and_usage")
                     else Paginator(client.get_cost_and_usage,
                                    {"input_token": "NextPageToken", "output_token": "NextPageToken",
                                     "result_key": "ResultsByTime"},
                                    client.meta.service_model.operation_model("GetCostAndUsage")))
        for page in paginator.paginate(
            TimePeriod={"Start": self.start.isoformat(), "End": self.end.isoformat()},
            Granularity="MONTHLY", Metrics=["UnblendedCost", "UsageQuantity"],
            Filter={"And": [{"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [account]}},
                             {"Not": {"Dimensions": {"Key": "RECORD_TYPE", "Values": ["Credit", "Refund"]}}}]},
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}, {"Type": "DIMENSION", "Key": "USAGE_TYPE"}],
        ):
            for period in page.get("ResultsByTime", []):
                for group in period.get("Groups", []):
                    service, usage = group["Keys"]
                    if service not in {"Elastic Load Balancing", "Amazon Elastic Load Balancing"} and not TRANSFER_PATTERN.search(usage):
                        continue
                    metrics = group["Metrics"]
                    rows.append({"month": period["TimePeriod"]["Start"][:7], "service": service,
                                 "usage_type": usage, "cost": metrics["UnblendedCost"]["Amount"],
                                 "currency": metrics["UnblendedCost"]["Unit"],
                                 "quantity": metrics["UsageQuantity"]["Amount"],
                                 "unit": metrics["UsageQuantity"]["Unit"], "estimated": period.get("Estimated", False)})
        return rows

    def describe_balancer(self, item: Json, region: str) -> Json:
        kind = item.get("Type", "classic")
        name = item["LoadBalancerName"]
        arn = item.get("LoadBalancerArn", "")
        service = "elb" if kind == "classic" else "elbv2"
        identity = {"LoadBalancerName": name} if kind == "classic" else {"LoadBalancerArn": arn}
        attributes = attempt(self.issues, f"ELB attributes {name}",
                             lambda: self.client(service, region).describe_load_balancer_attributes(**identity), {})
        if kind == "classic":
            logging = attributes.get("LoadBalancerAttributes", {}).get("AccessLog", {})
            attributes_map = {"access_logs.s3.enabled": str(logging.get("Enabled", False)).lower(),
                              "access_logs.s3.bucket": logging.get("S3BucketName", ""),
                              "access_logs.s3.prefix": logging.get("S3BucketPrefix", "")}
            listeners = [{"port": row["Listener"]["LoadBalancerPort"],
                          "protocol": row["Listener"]["Protocol"]} for row in item.get("ListenerDescriptions", [])]
            rules, groups = [], []
        else:
            attributes_map = {entry["Key"]: entry["Value"] for entry in attributes.get("Attributes", [])}
            raw_listeners = attempt(self.issues, f"ELB listeners {name}", lambda: self.pages(
                "elbv2", "describe_listeners", "Listeners", region, LoadBalancerArn=arn), [])
            listeners = [{"port": row["Port"], "protocol": row["Protocol"],
                          "actions": summarize_actions(row.get("DefaultActions", []))} for row in raw_listeners]
            rules = []
            if kind == "application":
                for listener in raw_listeners:
                    raw_rules = attempt(self.issues, f"ELB rules {name}:{listener['Port']}", lambda: self.pages(
                        "elbv2", "describe_rules", "Rules", region, ListenerArn=listener["ListenerArn"]), [])
                    for rule in raw_rules:
                        rules.append({"priority": rule["Priority"], "conditions": [
                            {"field": condition["Field"], "values": condition.get("Values", [])}
                            for condition in rule.get("Conditions", [])
                            if condition["Field"] in {"host-header", "path-pattern"}],
                            "actions": summarize_actions(rule.get("Actions", []))})
            raw_groups = attempt(self.issues, f"Target groups {name}", lambda: self.pages(
                "elbv2", "describe_target_groups", "TargetGroups", region, LoadBalancerArn=arn), [])
            groups = [{"name": group["TargetGroupName"], "arn": group["TargetGroupArn"],
                       "protocol": group.get("Protocol"), "port": group.get("Port"),
                       "type": group.get("TargetType"), "health_path": group.get("HealthCheckPath")}
                      for group in raw_groups]
        return {"name": name, "arn": arn, "region": region, "type": kind,
                "scheme": item.get("Scheme", "unknown"), "dns": normalize_host(item["DNSName"]),
                "created_at": str(item.get("CreatedTime", "unknown")),
                "attributes": attributes_map, "listeners": listeners, "rules": rules, "target_groups": groups}

    def metrics(self, balancer: Json) -> Json:
        kind = balancer["type"]
        namespace = {"application": "AWS/ApplicationELB", "network": "AWS/NetworkELB",
                     "gateway": "AWS/GatewayELB", "classic": "AWS/ELB"}[kind]
        dimension_name = "LoadBalancerName" if kind == "classic" else "LoadBalancer"
        dimension_value = balancer["name"] if kind == "classic" else balancer["arn"].split("loadbalancer/")[1]
        names = (["RequestCount", "EstimatedProcessedBytes"] if kind == "classic" else
                 ["ProcessedBytes", "RequestCount", "HTTPCode_Target_5XX_Count"] if kind == "application"
                 else ["ProcessedBytes", "NewFlowCount"])
        result = {}
        for metric in names:
            data = self.client("cloudwatch", balancer["region"]).get_metric_statistics(
                Namespace=namespace, MetricName=metric,
                Dimensions=[{"Name": dimension_name, "Value": dimension_value}],
                StartTime=utc_day(self.start), EndTime=utc_day(self.end), Period=86400, Statistics=["Sum"])
            daily = sorted([{"day": point["Timestamp"].date().isoformat(), "sum": point["Sum"]}
                            for point in data.get("Datapoints", [])], key=lambda point: point["day"])
            monthly: dict[str, Decimal] = defaultdict(Decimal)
            for point in daily:
                monthly[point["day"][:7]] += Decimal(str(point["sum"]))
            result[metric] = {"total": str(sum(monthly.values(), Decimal(0))) if daily else None,
                              "monthly": {month: str(value) for month, value in monthly.items()},
                              "daily": daily, "datapoints": len(daily)}
        return result

    def dns_records(self) -> list[Json]:
        records = []
        for zone in self.pages("route53", "list_hosted_zones", "HostedZones"):
            for page in self.client("route53").get_paginator("list_resource_record_sets").paginate(HostedZoneId=zone["Id"]):
                for record in page["ResourceRecordSets"]:
                    if record["Type"] not in {"A", "AAAA", "CNAME"}:
                        continue
                    targets = [record["AliasTarget"]["DNSName"]] if "AliasTarget" in record else [
                        value["Value"] for value in record.get("ResourceRecords", [])]
                    records.append({"name": normalize_host(record["Name"]),
                                    "targets": [normalize_host(target) for target in targets],
                                    "private": zone.get("Config", {}).get("PrivateZone", False)})
                    if len(records) >= 20000:
                        self.issues.append("Route 53: record collection capped at 20000")
                        return records
        return records

    def distributions(self) -> list[Json]:
        distributions = []
        for page in self.client("cloudfront").get_paginator("list_distributions").paginate():
            for item in page.get("DistributionList", {}).get("Items", []):
                behaviors = [item["DefaultCacheBehavior"], *item.get("CacheBehaviors", {}).get("Items", [])]
                distributions.append({"id": item["Id"], "domain": item["DomainName"], "enabled": item["Enabled"],
                                      "aliases": item.get("Aliases", {}).get("Items", []),
                                      "origins": [{"id": origin["Id"], "domain": normalize_host(origin["DomainName"]),
                                                   "path": origin.get("OriginPath", "")}
                                                  for origin in item["Origins"]["Items"]],
                                      "behaviors": [{"path": row.get("PathPattern", "*"),
                                                     "origin": row["TargetOriginId"], "compress": row.get("Compress"),
                                                     "cache_policy_id": row.get("CachePolicyId"),
                                                     "default_ttl": row.get("DefaultTTL"),
                                                     "forward_query_string": row.get("ForwardedValues", {}).get("QueryString")}
                                                    for row in behaviors]})
        return distributions


def summarize_actions(actions: list[Json]) -> list[Json]:
    # Authentication actions can contain client secrets; never persist raw actions.
    return [{"type": action["Type"], "target_groups": list(dict.fromkeys(
        ([action["TargetGroupArn"]] if action.get("TargetGroupArn") else []) +
        [group["TargetGroupArn"] for group in action.get("ForwardConfig", {}).get("TargetGroups", [])]))}
        for action in actions]


def link_domains(balancers: list[Json], records: list[Json], cdns: list[Json]) -> None:
    for balancer in balancers:
        domains = {balancer["dns"]}
        for _ in range(12):
            additions = {record["name"] for record in records if domains.intersection(record["targets"])}
            if additions.issubset(domains):
                break
            domains.update(additions)
        balancer["direct_domains"] = sorted(domains)
        balancer["rule_hosts"] = sorted({host for rule in balancer["rules"] for condition in rule["conditions"]
                                          if condition["field"] == "host-header" for host in condition["values"]})
        balancer["cloudfront_ids"] = [cdn["id"] for cdn in cdns if any(
            origin["domain"] in domains for origin in cdn["origins"])]
        balancer["cdn_domains"] = sorted({host for cdn in cdns if cdn["id"] in balancer["cloudfront_ids"]
                                          for host in [cdn["domain"], *cdn["aliases"]]})
