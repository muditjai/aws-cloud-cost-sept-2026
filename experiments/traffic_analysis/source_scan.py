"""Deterministic code signals. Matches are review candidates, never proof of cost."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import PurePosixPath
from urllib.parse import quote

from .common import Json, Redactor, normalize_host
from urllib.parse import urlsplit

SKIP_PARTS = {"node_modules", ".git", ".next", "vendor", "vendors", "dist", "build", "coverage",
              "pods", ".venv", "venv", "__pycache__", "bower_components", "third_party", "third-party"}
EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".swift", ".m", ".mm", ".h",
              ".php", ".rb", ".go", ".rs", ".cs", ".tf", ".json", ".yaml", ".yml", ".conf", ".config",
              ".xml", ".properties", ".ini", ".html", ".htm", ".vue", ".svelte", ".sh", ".gradle"}

# Each rule contains a mechanism and a conditional, concrete remediation.
RULES = [
    ("media_proxy", 8, r"send_file\s*\(|sendFile\s*\(|FileResponse\s*\(|StreamingResponse\s*\(|"
     r"createReadStream\s*\(|getObject\s*\(|GetObjectCommand\s*\(|readfile\s*\(|"
     r"proxy_pass\s|\.pipe\s*\(\s*(?:res|response)|StreamingResponseBody|InputStreamResource",
     "Server-side file or upstream streaming",
     "Trace this handler to a high-byte route. For immutable media, return an authorized CDN URL or redirect "
     "and deliver from private object storage through CloudFront; preserve access controls and Range/206 support."),
    ("media_delivery", 5, r"audio/(?:mpeg|wav|mp4)|video/mp4|\.mp3\b|\.m4a\b|\.wav\b|\.m3u8\b|"
     r"Content-Disposition|content_length|Content-Length|send_data\s|response\.body\(\)",
     "Potential large media response or download",
     "Check actual bytes and request counts for this path; use an appropriate audio codec/bitrate and "
     "serve immutable content through a CDN. Verify that seeking returns partial content rather than a full download."),
    ("cache_disabled", 7, r"no-store|no-cache|(?:max[_-]?age|default_ttl|max_ttl)\s*[=:]\s*[\"']?0\b|"
     r"cache\s*:\s*false|CachingDisabled|413f160d-6f8e-4b1b-b2f3-3a317bb97b1d",
     "Caching is bypassed or requires revalidation",
     "If the response is public and immutable, use versioned URLs and a positive cache lifetime. "
     "Keep private/user-specific responses private; do not remove no-store without reviewing authorization and cache keys."),
    ("cache_buster", 6, r"[?&](?:_+|t|ts|timestamp|cacheBust|nocache)\s*=|[?&][\w-]*=[\"'`]?\s*\+\s*(?:Date|new Date)|"
     r"cache[bB]ust|cache:\s*[\"']reload",
     "URL or request behavior may bypass shared caching",
     "Replace per-request timestamps with a content version/hash for immutable assets. Exclude only verified "
     "non-content query parameters from the CDN cache key; retain signed-URL authorization checks."),
    ("polling", 4, r"setInterval\s*\(|refetchInterval\s*:|pollInterval|retry\s*:\s*(?:true|[3-9])|"
     r"scheduleAtFixedRate\s*\(|Timer\.periodic|time\.sleep\(",
     "Repeated work, polling, or retries",
     "Check whether this loop performs network requests. Add cancellation on unmount/background, deduplicate "
     "in-flight requests, use bounded exponential backoff, and reduce polling after measuring payload sizes."),
    ("preload", 6, r"preload\s*[=:]\s*[\"']auto|\.preload\s*=|prefetch\s*[=:]\s*true|"
     r"new Audio\s*\(|AVPlayerItem\s*\(|\.load\s*\(\s*\)",
     "Playback may fetch data before explicit demand",
     "Inspect player lifecycle for repeated downloads. Start with preload=none or metadata, defer media requests "
     "until play, reuse the active source, and cancel obsolete requests; verify startup latency and seeking."),
    ("buffering", 5, r"arrayBuffer\s*\(|\.blob\s*\(|readAllBytes\s*\(|\.base64\b|b64encode\s*\(|"
     r"responseType\s*:\s*[\"'](?:blob|arraybuffer)|base64EncodedString",
     "Whole response buffering or binary encoding",
     "Check whether playback downloads an entire media object before use. Prefer URL/range-based playback "
     "and avoid embedding binary/base64 payloads inside API JSON when a protected media URL is sufficient."),
    ("infrastructure", 3, r"aws_lb\b|aws_alb\b|aws_elb\b|aws_cloudfront_distribution|"
     r"aws_cloudfront_cache_policy|elasticloadbalancing|\.elb\.amazonaws\.com|"
     r"proxy_cache|gzip\s+off|compression\s*[:=]\s*false",
     "Load balancer, cache, or response compression configuration",
     "Map this configuration to the discovered live resource. Review cache behavior, origin routing, and "
     "compression for text/JSON; already compressed audio typically gains little from gzip."),
]
COMPILED = [(name, score, re.compile(pattern, re.I), title, action)
            for name, score, pattern, title, action in RULES]


def eligible_source(path: str) -> bool:
    candidate = PurePosixPath(path)
    parts = {part.lower() for part in candidate.parts}
    name = candidate.name.lower()
    if candidate.is_absolute() or ".." in candidate.parts or parts & SKIP_PARTS:
        return False
    if name.startswith(".env") or re.search(r"(?:secret|credential|private[_-]?key|service[-_]?account)", name):
        return False
    if name.endswith((".min.js", ".map", "lock.json", ".lock", "-lock.yaml")):
        return False
    return candidate.suffix.lower() in EXTENSIONS or name in {"dockerfile", "nginx.conf", "gemfile"}


def build_indicators(aws: Json) -> list[Json]:
    indicators = []
    volumes = {balancer["name"]: Decimal(balancer.get("metrics", {}).get("ProcessedBytes", {}).get("total") or "0")
               for balancer in aws.get("load_balancers", [])}
    total = sum(volumes.values(), Decimal(0))
    for balancer in aws.get("load_balancers", []):
        for host in balancer.get("direct_domains", [balancer["dns"]]):
            if not host.startswith("*."):
                indicators.append({"text": host, "balancer": balancer["name"], "kind": "direct_host"})
        for host in balancer.get("cdn_domains", []):
            indicators.append({"text": host, "balancer": balancer["name"], "kind": "cdn_host"})
        for host in balancer.get("rule_hosts", []):
            if not host.startswith("*."):
                indicators.append({"text": host, "balancer": balancer["name"], "kind": "listener_host"})
        for route in balancer.get("access_logs", {}).get("routes", [])[:25]:
            path = route["path"]
            if len(path) >= 5 and "{id}" not in path and path not in {"/api/health", "/favicon.ico", "/robots.txt"}:
                indicators.append({"text": path, "host": route["host"], "balancer": balancer["name"], "kind": "observed_path"})
    for indicator in indicators:
        share = volumes.get(indicator["balancer"], Decimal(0)) / total if total else Decimal(0)
        indicator["traffic_priority"] = 6 if share >= Decimal("0.2") else 3 if share >= Decimal("0.05") else 0
    return indicators


def indicator_matches(indicator: Json, source: str) -> bool:
    """Match complete DNS names, not a parent domain embedded in another hostname."""
    text = re.escape(indicator["text"])
    if indicator["kind"] == "observed_path":
        # Require a URL or request-path literal, not an import such as @/types/player.
        prefix = r"(?:https?://[^\s\"'`/]+|\$[A-Za-z_]\w*|[\"'`}]|\\\))"
        for match in re.finditer("(?P<prefix>" + prefix + ")" + text + r"(?![\w./-])", source, re.I):
            before = match.group("prefix")
            if before.lower().startswith(("http://", "https://")) and indicator.get("host"):
                if normalize_host(urlsplit(before).hostname or "") != normalize_host(indicator["host"]):
                    continue
            return True
        return False
    return bool(re.search(r"(?<![\w.-])" + text + r"(?![\w.-])", source, re.I))


def scan_source(repo: str, commit: str, path: str, source: str,
                indicators: list[Json], redactor: Redactor) -> list[Json]:
    lines = source.splitlines()
    # Treat generated/minified files as opaque even if their filename is innocent.
    if not lines or max(map(len, lines)) > 3000:
        return []
    findings = []
    file_links = [indicator for indicator in indicators if indicator_matches(indicator, source)]
    matches: dict[tuple[str, int], Json] = {}
    for rule, score, pattern, title, action in COMPILED:
        count = 0
        for index, line in enumerate(lines):
            if line.lstrip().startswith(("//", "#", "*", "<!--")):
                continue
            if pattern.search(line):
                matches[(rule, index)] = {"rule": rule, "score": score, "title": title, "action": action}
                count += 1
                if count >= 6:
                    break
    for indicator in file_links:
        count = 0
        for index, line in enumerate(lines):
            if line.lstrip().startswith(("//", "#", "*", "<!--")):
                continue
            if indicator_matches(indicator, line):
                matches.setdefault(("aws_reference", index), {
                    "rule": "aws_reference", "score": 4, "title": "Reference to an observed AWS host or route",
                    "action": "Trace this caller or route to its deployed handler and compare with sampled response bytes. "
                              "For direct media URLs, consider a protected CDN URL after validating the route's purpose."})
                count += 1
                if count >= 6:
                    break
    for (_, index), details in matches.items():
        first, last = max(0, index - 4), min(len(lines), index + 7)
        context = "\n".join(lines[first:last])
        links = [indicator for indicator in file_links if indicator_matches(indicator, context)]
        test_file = bool(re.search(r"(?:^|/)(?:test[s]?|spec|examples?|demo)(?:/|\.)|\.(?:test|spec)\.", path, re.I))
        findings.append({**details, "repo": repo, "commit": commit, "path": path, "line": index + 1,
                         "url": f"https://github.com/{repo}/blob/{commit}/{quote(path, safe='/')}#L{index + 1}",
                         "snippet": redactor.clean("\n".join(f"{number + 1}: {lines[number]}" for number in range(first, last))),
                         "aws_links": links, "file_aws_links": file_links[:10], "test_or_example": test_file,
                         "score": details["score"] + (8 if links else 3 if file_links else 0)
                         + max((link.get("traffic_priority", 0) for link in links), default=0)
                         + (5 if any(link["kind"] == "observed_path" for link in links) else 0)
                         - (5 if test_file else 0),
                         "confidence": "code signal; runtime causality unconfirmed"})
    return findings


def revalidate_findings(findings: list[Json], aws: Json) -> list[Json]:
    """Recheck saved snippets against current matching rules when regenerating reports."""
    indicators = build_indicators(aws)
    results = []
    base_scores = {rule[0]: rule[1] for rule in RULES}
    titles = {rule[0]: rule[3] for rule in RULES}
    file_associations: dict[tuple[str, str], list[Json]] = {}
    for finding in findings:
        identity = (finding["repo"], finding["path"])
        source = re.sub(r"(?m)^\d+: ", "", finding["snippet"])
        source = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith(("//", "#", "*", "<!--")))
        associated = file_associations.setdefault(identity, [])
        for indicator in indicators:
            if indicator not in associated and indicator_matches(indicator, source):
                associated.append(indicator)
    for finding in findings:
        source = re.sub(r"(?m)^\d+: ", "", finding["snippet"])
        numbered = dict(re.findall(r"(?m)^(\d+): (.*)$", finding["snippet"]))
        matched_line = numbered.get(str(finding["line"]), "")
        if matched_line.lstrip().startswith(("//", "#", "*", "<!--")):
            continue
        if finding["rule"] == "aws_reference" and not any(indicator_matches(item, matched_line) for item in indicators):
            continue
        links = [indicator for indicator in indicators if indicator_matches(indicator, source)]
        # Re-prove file associations from retained snippets, not historical substring matches.
        file_links = file_associations[(finding["repo"], finding["path"])][:10]
        finding = {**finding, "aws_links": links, "file_aws_links": file_links}
        finding["title"] = titles.get(finding["rule"], finding["title"])
        finding["score"] = (base_scores.get(finding["rule"], 4) + (8 if links else 3 if file_links else 0)
                            + max((item.get("traffic_priority", 0) for item in links), default=0)
                            + (5 if any(item["kind"] == "observed_path" for item in links) else 0)
                            - (5 if finding["test_or_example"] else 0))
        results.append(finding)
    return results
