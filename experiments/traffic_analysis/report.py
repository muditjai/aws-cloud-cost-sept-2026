"""Render auditable Markdown with deterministic arithmetic and explicit coverage."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .common import Json
from .llm_review import choose_findings
from .action_plan import action_plan

BASELINE = [
    ("2026-04", "1922.59", "1423.30"), ("2026-05", "2287.02", "1763.26"),
    ("2026-06", "1644.52", "1207.72"), ("2026-07", "1860.77", "1343.54"),
    ("2026-08", "2116.51", "1555.43"), ("2026-09*", "2169.55", "1667.24"),
]


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;")


def gib(value: object) -> str:
    return f"{Decimal(str(value)) / Decimal(1024 ** 3):,.2f}" if value is not None else "unavailable"


def render_report(evidence: Json) -> str:
    aws = evidence.get("aws", {})
    balancers = aws.get("load_balancers", [])
    rows = ["# Load balancer traffic and source-code investigation", "",
            f"Generated: {evidence['generated_at']}. Billing/metrics: {evidence['start']} through "
            f"{evidence['end']} (end exclusive).", "",
            "## What the evidence can establish", "",
            "This is a read-only investigation. No cloud resources, repositories, or access-log settings were changed. "
            "Code matches are review candidates, not confirmed causes of billed charges. The default-branch commits "
            "scanned here have not been verified as the versions deployed during the billing period.", "",
            "Cost Explorer is scoped to the authenticated AWS account and excludes credits/refunds. "
            "Current inventory can miss load balancers deleted during the billing period. "
            "`ProcessedBytes` includes both directions; `sent_bytes` is application response traffic in sampled logs. "
            "Neither is equal to billed internet egress, and no per-load-balancer dollar allocation is inferred.", ""]
    total = sum((Decimal(row[1]) for row in BASELINE), Decimal(0))
    outbound = sum((Decimal(row[2]) for row in BASELINE), Decimal(0))
    def measured_bytes(balancer: Json) -> Decimal:
        metrics = balancer.get("metrics", {})
        return Decimal(metrics.get("ProcessedBytes", metrics.get("EstimatedProcessedBytes", {})).get("total") or "0")
    measured_total = sum((measured_bytes(item) for item in balancers), Decimal(0))
    if measured_total:
        largest = max(balancers, key=measured_bytes)
        rows += ["## Where to start", "",
                 f"**{largest['name']}** is the largest observed traffic source among discovered load balancers: "
                 f"**{gib(measured_bytes(largest))} GiB** processed in the requested period "
                 f"(**{measured_bytes(largest) / measured_total * 100:.2f}%** of available processed-byte metrics). "
                 "This is a traffic ranking, not an allocation of billed egress dollars.", ""]
        logs = largest.get("access_logs", {})
        if logs.get("routes"):
            top = logs["routes"][0]
            rows += [f"The largest response-byte route in its bounded log sample is **{cell(top['method'])} "
                     f"{cell(top['host'] + top['path'])}**. Start by locating its handler and "
                     "the static assets loaded by that page. Verify caching, compression, repeated iframe/page loads, "
                     "and client initialization before assuming audio delivery is responsible.", ""]
    rows += action_plan(evidence)
    rows += ["## User-supplied billing baseline", "",
             f"Total **${total:,.2f}**; DataTransfer-Out-Bytes **${outbound:,.2f}** "
             f"(**{outbound / total * 100:.2f}%**). This supplied baseline is distinct from live AWS results.", "",
             "| Month | Total USD | DataTransfer-Out-Bytes USD |", "| --- | ---: | ---: |"]
    rows += [f"| {month} | {Decimal(cost):,.2f} | {Decimal(transfer):,.2f} |" for month, cost, transfer in BASELINE]
    rows += ["", "*September was marked estimated/partial in the supplied bill; it is not treated as a finalized trend.", "",
             "## Live billing evidence", ""]
    billing = aws.get("billing", [])
    if not billing:
        rows += ["Live billing was unavailable, skipped, or returned no matching rows. See coverage gaps below.", ""]
    else:
        totals: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
        monthly: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for entry in billing:
            totals[(entry["service"], entry["usage_type"], entry["currency"])] += Decimal(entry["cost"])
            if "DataTransfer-Out-Bytes" in entry["usage_type"]:
                monthly[(entry["month"], entry["currency"])] += Decimal(entry["cost"])
        rows += ["Transfer charges are shown across services so an EC2 transfer charge is not silently "
                 "relabelled as an ELB capacity charge. Full per-month quantities/units are in the JSON evidence.", "",
                 "| Service | Usage type | Cost | Currency |", "| --- | --- | ---: | --- |"]
        for (service, usage, currency), cost in sorted(totals.items(), key=lambda pair: pair[1], reverse=True)[:40]:
            rows.append(f"| {cell(service)} | {cell(usage)} | {cost:,.2f} | {currency} |")
        rows += ["", "| Month | DataTransfer-Out-Bytes across services | Currency |", "| --- | ---: | --- |"]
        rows += [f"| {month} | {cost:,.2f} | {currency} |" for (month, currency), cost in sorted(monthly.items())]
        rows += ["", f"Estimated billing rows present: {any(row['estimated'] for row in billing)}.", ""]
    rows += ["## Load balancers and measured volume", "",
             "| Name | Region / type / scheme | Processed GiB in period | Requests in period | S3 access logs |",
             "| --- | --- | ---: | ---: | --- |"]
    def volume(balancer: Json) -> Decimal:
        metrics = balancer.get("metrics", {})
        return Decimal(metrics.get("ProcessedBytes", metrics.get("EstimatedProcessedBytes", {})).get("total") or "0")
    for balancer in sorted(balancers, key=volume, reverse=True):
        metrics = balancer.get("metrics", {})
        processed = metrics.get("ProcessedBytes", metrics.get("EstimatedProcessedBytes", {})).get("total")
        requests = metrics.get("RequestCount", {}).get("total")
        rows.append(f"| {cell(balancer['name'])} | {balancer['region']} / {balancer['type']} / {balancer['scheme']} "
                    f"| {gib(processed)} | {requests or 'unavailable'} | {cell(balancer.get('access_logs', {}).get('status', 'not collected'))} |")
    if not balancers:
        rows.append("| No load balancers discovered; see coverage gaps | | | | |")
    rows += ["", "Missing CloudWatch datapoints are not zero traffic. Classic ELB byte metrics are estimates. "
             "Historical CloudWatch retention can also limit coverage; daily datapoint counts are in JSON.", ""]
    for balancer in sorted(balancers, key=volume, reverse=True):
        rows += [f"### {cell(balancer['name'])}", "", f"- DNS: `{balancer['dns']}`",
                 f"- ARN: `{balancer['arn'] or 'classic ELB identified by name'}`",
                 f"- Direct DNS aliases: {', '.join(balancer.get('direct_domains', [])) or 'none discovered'}",
                 f"- Listener hosts: {', '.join(balancer.get('rule_hosts', [])) or 'none discovered'}",
                 f"- CloudFront distributions using this origin: {', '.join(balancer.get('cloudfront_ids', [])) or 'none discovered'}",
                 f"- CDN domains: {', '.join(balancer.get('cdn_domains', [])) or 'none discovered'}",
                 f"- Target groups: {', '.join(group['name'] for group in balancer.get('target_groups', [])) or 'none discovered'}", ""]
        metrics = balancer.get("metrics", {})
        processed = metrics.get("ProcessedBytes", metrics.get("EstimatedProcessedBytes", {}))
        if processed.get("monthly"):
            rows += ["| Month | Processed GiB |", "| --- | ---: |"]
            rows += [f"| {month} | {gib(value)} |" for month, value in sorted(processed["monthly"].items())]
            rows.append("")
        logs = balancer.get("access_logs", {})
        if logs.get("routes"):
            rows += [f"Sample: {logs['objects_read']} objects; {logs['total_requests']:,} requests; "
                     f"{gib(logs['total_sent_bytes'])} GiB sent. Observed timestamps: {logs['first_timestamp']} to {logs['last_timestamp']}.", "",
                     "This is a bounded, non-random sample. Shares below describe this sample only and are not "
                     "projected to monthly traffic or savings.", "",
                     "| Method / host / path | Requests | Sent GiB | Sample byte share | Status counts |",
                     "| --- | ---: | ---: | ---: | --- |"]
            for route in logs["routes"][:15]:
                share = Decimal(route["sent_bytes"]) / Decimal(logs["total_sent_bytes"]) * 100 if logs["total_sent_bytes"] else Decimal(0)
                rows.append(f"| {cell(route['method'] + ' ' + route['host'] + route['path'])} | {route['requests']:,} "
                            f"| {gib(route['sent_bytes'])} | {share:.2f}% | {cell(route['statuses'])} |")
            rows.append("")
        else:
            rows += ["No endpoint-level sample was collected. If S3 logs are disabled, enable access logging "
                     "after review, or export existing CloudWatch/Firehose/application logs. This tool reads "
                     "the existing S3 gzip text delivery only. Collect response bytes, route template, status, "
                     "Range behavior and cache status before attributing this resource's traffic to code.", ""]
    selected = choose_findings(evidence.get("findings", []), 45)
    by_id = {row["id"]: row for row in evidence.get("findings", [])}
    rows += ["## Prioritized source-code review", "",
             "Rank is a deterministic review priority, not a probability or savings estimate. AWS links in the "
             "same snippet are stronger than a host appearing elsewhere in a file. Both require deployment verification.", ""]
    if not selected:
        rows += ["No source findings are available. Repository access failures and scan limits are listed below.", ""]
    for finding in selected:
        links = finding["aws_links"]
        associations = ", ".join(sorted({f"{link['balancer']} ({link['kind']}: {link['text']})" for link in links}))
        rows += [f"### {finding['id']}: {finding['title']}", "",
                 f"Source: [{cell(finding['repo'] + '/' + finding['path'])}:{finding['line']}]({finding['url']}). "
                 f"Priority score: {finding['score']}. {'Test/example file.' if finding['test_or_example'] else ''}", "",
                 f"AWS association in snippet: {associations or 'none; code-only hypothesis'}.", ""]
        if not links and finding.get("file_aws_links"):
            rows += ["Elsewhere in this file: " + ", ".join(sorted({link["balancer"] + " via " + link["text"]
                       for link in finding["file_aws_links"]})) + ". This does not prove the same execution path.", ""]
        rows += ["````text", finding["snippet"].replace("````", "[fence]"), "````", "",
                 f"Action: {finding['action']}", ""]
    llm = evidence.get("llm", {})
    rows += ["## Optional LLM review", "", f"Status: {cell(llm.get('status', 'not requested'))}.", ""]
    if llm.get("actions"):
        rows += [f"Model: `{llm['model']}`. These proposals need human/code review. Citation IDs are validated "
                 "against supplied evidence; their reasoning is not independently verified.", ""]
        for index, action in enumerate(llm["actions"], 1):
            citations = ", ".join(f"[{identifier}]({by_id[identifier]['url']})" for identifier in action["evidence_ids"])
            rows += [f"### {index}. {action['title']}", "", f"Evidence: {citations}", ""]
            for note in action.get("review_notes", []):
                rows += [f"**Review note:** {note}", ""]
            rows += [action["mechanism"], "", f"Model-proposed code change: {action['proposed_change']}", "",
                     f"Validate: {action['verification']}", "", f"Uncertainty: {action['uncertainty']}", ""]
    rows += ["## Measure before changing delivery", "",
             "1. Confirm which commit/service is deployed behind the target group. Match the top response-byte "
             "routes with source handlers and callers; resolve any reverse-proxy path rewriting.",
             "2. Capture a comparable baseline of sent bytes, request count, playback errors, and 200/206 status "
             "mix. Test initial play, seeking, repeat play, unmount, authentication expiry, and background tabs.",
             "3. Trial the specific change on a small traffic cohort. For CDN changes measure cache-hit ratio, "
             "origin bytes, viewer bytes and CDN costs; retaining viewer delivery charges can offset origin savings.",
             "4. Reconcile the following full billing period by account, region and usage type. Use CUR resource "
             "IDs where available for dollar attribution. Do not multiply sampled byte shares by the whole bill.", "",
             "## Coverage and limitations", "",
             f"AWS status: {aws.get('status', 'skipped')}. Regions: {', '.join(aws.get('regions', [])) or 'none'}. "
             f"Source findings retained: {len(evidence.get('findings', []))}.", "",
             "| Repository | Status | Files scanned | Candidate count | Commit | Limits |",
             "| --- | --- | ---: | ---: | --- | --- |"]
    for repo in sorted(evidence.get("repositories", []), key=lambda row: row["repo"].lower()):
        rows.append(f"| {cell(repo['repo'])} | {cell(repo['status'])} | {repo.get('files_scanned', 0)} "
                    f"| {repo.get('candidate_count', 0)} | {repo.get('commit', '')[:12]} | {cell('; '.join(repo.get('limitations', [])))} |")
    rows += ["", "Repository scan scope: default-branch snapshot; common source/config formats only; no history, "
             "submodules, LFS objects, dependencies, generated/minified files, secrets or oversized files. "
             "Code outside this scope may contain the cause. All retained findings are in the companion JSON.", ""]
    rows += [f"- {cell(issue)}" for issue in evidence.get("issues", [])] or ["- No API collection errors recorded."]
    rows += ["", "## Reference semantics", "",
             "- [ALB access logs and sent_bytes](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html)",
             "- [ALB CloudWatch metric definitions](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html)",
             "- [Cost Explorer GetCostAndUsage](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_GetCostAndUsage.html)",
             "- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)", ""]
    return "\n".join(rows)
