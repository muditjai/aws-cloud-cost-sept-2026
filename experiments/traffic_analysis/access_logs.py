"""Bounded S3 log sampling, with no raw requests or client addresses retained."""

from __future__ import annotations

import gzip
import io
import shlex
from datetime import date, datetime, timedelta

from .aws_evidence import AwsCollector
from .common import Json, attempt, route_key, utc_day


def parse_log(line: str, classic: bool = False) -> Json | None:
    try:
        fields = shlex.split(line)
        offset = 0 if classic else 1
        if not classic and fields[0] not in {"http", "https", "h2", "grpcs", "ws", "wss"}:
            return None  # NLB TLS logs have no HTTP endpoint/response byte attribution.
        timestamp = datetime.fromisoformat(fields[offset].replace("Z", "+00:00"))
        method, host, path = route_key(fields[11 + offset])
        return {"timestamp": timestamp, "balancer_id": fields[1 + offset], "method": method,
                "host": host, "path": path, "sent_bytes": max(0, int(fields[10 + offset])),
                "status": fields[7 + offset],
                "target_group": "" if classic or len(fields) < 17 or fields[16] == "-" else fields[16]}
    except (ValueError, IndexError):
        return None


def aggregate_lines(lines: list[str], balancer: Json, start: date, end: date) -> Json:
    routes: dict[tuple[str, str, str], Json] = {}
    malformed, outside, first, last = 0, 0, None, None
    expected = balancer["name"] if balancer["type"] == "classic" else balancer["arn"].split("loadbalancer/")[1]
    for line in lines:
        row = parse_log(line, balancer["type"] == "classic")
        if row is None:
            malformed += 1
            continue
        if row["balancer_id"] != expected or not utc_day(start) <= row["timestamp"] < utc_day(end):
            outside += 1
            continue
        first = min(first, row["timestamp"]) if first else row["timestamp"]
        last = max(last, row["timestamp"]) if last else row["timestamp"]
        identity = (row["method"], row["host"], row["path"])
        if identity not in routes:
            routes[identity] = {"method": row["method"], "host": row["host"], "path": row["path"],
                                "requests": 0, "sent_bytes": 0, "statuses": {}, "target_groups": []}
        route = routes[identity]
        route["requests"] += 1
        route["sent_bytes"] += row["sent_bytes"]
        status = row["status"]
        route["statuses"][status] = route["statuses"].get(status, 0) + 1
        if row["target_group"] and row["target_group"] not in route["target_groups"]:
            route["target_groups"].append(row["target_group"])
    return {"routes": list(routes.values()), "malformed_lines": malformed, "excluded_lines": outside,
            "first_timestamp": str(first) if first else None, "last_timestamp": str(last) if last else None}


def sample_logs(collector: AwsCollector, balancer: Json, account: str, start: date,
                end: date, max_objects: int, max_bytes: int) -> Json:
    attributes = balancer["attributes"]
    enabled = attributes.get("access_logs.s3.enabled") == "true"
    result: Json = {"status": "disabled" if not enabled else "unavailable", "routes": [], "objects_read": 0,
                    "window_start": str(start), "window_end_exclusive": str(end),
                    "sampling": "Most recent days first; bounded objects, not a representative sample."}
    if balancer["type"] not in {"application", "classic"}:
        result["status"] = "unsupported: NLB/GWLB logs do not provide HTTP route byte totals"
        return result
    if not enabled or max_objects == 0:
        if max_objects == 0:
            result["status"] = "skipped"
        return result
    bucket = attributes.get("access_logs.s3.bucket", "")
    prefix = attributes.get("access_logs.s3.prefix", "").strip("/")
    base = "/".join(part for part in [prefix, "AWSLogs", account, "elasticloadbalancing", balancer["region"]] if part)
    client = collector.client("s3", balancer["region"])
    expected = balancer["name"] if balancer["type"] == "classic" else balancer["arn"].split("loadbalancer/")[1].replace("/", ".")
    candidates = []
    scanned = 0
    for day_offset in range((end - start).days):
        day = end - timedelta(days=day_offset + 1)
        day_prefix = f"{base}/{day:%Y/%m/%d}/"
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=day_prefix):
            for item in page.get("Contents", []):
                scanned += 1
                if f"_{expected}_" in item["Key"] and item["Key"].endswith((".log.gz", ".log")):
                    candidates.append(item)
            if len(candidates) >= max_objects or scanned >= 10000:
                break
        if len(candidates) >= max_objects or scanned >= 10000:
            break
    candidates.sort(key=lambda item: item["LastModified"], reverse=True)
    routes: dict[tuple[str, str, str], Json] = {}
    total_bytes, malformed, excluded = 0, 0, 0
    times = []
    for item in candidates[:max_objects]:
        remaining = max_bytes - total_bytes
        if remaining <= 0 or item["Size"] > remaining:
            collector.issues.append(f"S3 log byte limit reached for {balancer['name']}")
            if remaining <= 0:
                break
            continue
        def read_object() -> bytes:
            with client.get_object(Bucket=bucket, Key=item["Key"])["Body"] as body:
                return body.read(remaining + 1)
        compressed = attempt(collector.issues, f"S3 log read {balancer['name']}", read_object, b"")
        if not compressed:
            continue
        if len(compressed) > remaining:
            collector.issues.append(f"S3 compressed log exceeded byte limit for {balancer['name']}")
            break
        def decode_object() -> bytes:
            if not item["Key"].endswith(".gz"):
                return compressed
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
                return stream.read(remaining + 1)
        decoded = attempt(collector.issues, f"S3 log decompress {balancer['name']}", decode_object, b"")
        if len(decoded) > remaining:
            collector.issues.append(f"S3 expanded log partially sampled at byte limit for {balancer['name']}")
            decoded = decoded[:remaining].rsplit(b"\n", 1)[0]
            result["partial_object"] = True
        total_bytes += len(decoded)
        summary = aggregate_lines(decoded.decode("utf-8", errors="replace").splitlines(), balancer, start, end)
        result["objects_read"] += 1
        malformed += summary["malformed_lines"]
        excluded += summary["excluded_lines"]
        times.extend(value for value in [summary["first_timestamp"], summary["last_timestamp"]] if value)
        for row in summary["routes"]:
            identity = (row["method"], row["host"], row["path"])
            if identity not in routes:
                routes[identity] = row
            else:
                routes[identity]["requests"] += row["requests"]
                routes[identity]["sent_bytes"] += row["sent_bytes"]
                for status, count in row["statuses"].items():
                    routes[identity]["statuses"][status] = routes[identity]["statuses"].get(status, 0) + count
                routes[identity]["target_groups"] = sorted(set(routes[identity]["target_groups"] + row["target_groups"]))
    result.update({"status": "sampled" if result["objects_read"] else "no readable matching objects",
                   "routes": sorted(routes.values(), key=lambda row: row["sent_bytes"], reverse=True)[:100],
                   "total_sent_bytes": sum(row["sent_bytes"] for row in routes.values()),
                   "total_requests": sum(row["requests"] for row in routes.values()),
                   "expanded_bytes_read": total_bytes, "malformed_lines": malformed, "excluded_lines": excluded,
                   "first_timestamp": min(times) if times else None, "last_timestamp": max(times) if times else None,
                   "listing_objects_examined": scanned, "object_limit": max_objects,
                   "route_count_before_limit": len(routes)})
    return result
