"""Translate matched runtime paths and code excerpts into conditional review tasks."""

from __future__ import annotations

import re

from .common import Json


def citations(findings: list[Json], limit: int = 3) -> str:
    seen = set()
    links = []
    for finding in findings:
        identity = (finding["repo"], finding["path"])
        if identity in seen:
            continue
        seen.add(identity)
        label = f"{finding['repo']}/{finding['path']}:{finding['line']}".replace("|", "\\|")
        links.append(f"[{label}]({finding['url']})")
        if len(links) >= limit:
            break
    return "; ".join(links)


def action_plan(evidence: Json) -> list[str]:
    findings = sorted(evidence.get("findings", []), key=lambda row: row["score"], reverse=True)
    rows = ["## First code changes to review", "",
            "These are conditional proposals tied to observed routes or live resource references. "
            "Confirm deployment and response headers before changing behavior.", ""]
    assets = [finding for finding in findings if any(link["kind"] == "observed_path"
              and link["text"].startswith(("/js/", "/images/", "/_next/")) for link in finding["aws_links"])]
    if assets:
        rows += ["1. **Reduce repeat delivery of player assets.** The sampled JavaScript/images reach the load "
                 "balancer. Update the matched asset references to a versioned asset/CDN base URL and configure "
                 "the serving layer with a long public cache lifetime only for immutable, non-personalized files. "
                 "Keep short lifetimes for filenames whose content changes without a version bump. "
                 "Use content hashes or bump versions on release. Check compression for JS/SVG and "
                 "optimize the shared logo/ad image sizes. Validate repeat page loads: fewer origin 200/304 "
                 "requests, fewer sent bytes, and unchanged assets. Existing CDN or browser cache behavior "
                 "must be measured; this proposal does not imply it is absent.", "", "   References: " + citations(assets), ""]
    embeds = [finding for finding in findings if re.search(r"iframe\.src\s*=|setAttribute\([^\n]*src", finding["snippet"])
              and any(link["kind"] == "observed_path" for link in finding["aws_links"])]
    if embeds:
        rows += ["2. **Review player iframe initialization.** At the iframe source assignment, guard repeated "
                 "initialization and avoid assigning the same URL on rerenders or duplicate embed execution. "
                 "Defer off-screen player creation where product behavior permits; preserve playback start "
                 "and accessibility. Duplicate loading is a hypothesis, not established by these snippets. "
                 "Verify one initial player document request per intended instance using a browser network trace.", "",
                 "   References: " + citations(embeds), ""]
    proxy_findings = []
    target_names = set()
    for balancer in evidence.get("aws", {}).get("load_balancers", []):
        if balancer["scheme"] != "internet-facing":
            continue
        for finding in findings:
            if re.search(r"server\s+" + re.escape(balancer["dns"]) + r"(?=[:;\s])", finding["snippet"], re.I):
                proxy_findings.append(finding)
                target_names.add(balancer["name"])
    if proxy_findings:
        rows += ["3. **Verify public load balancers used as internal upstreams.** The Nginx source points to "
                 + ", ".join(f"`{name}`" for name in sorted(target_names))
                 + ". If this configuration is deployed, trace the server-to-server hop and evaluate an "
                 "internal endpoint/service discovery for that upstream. Review the nearby static-asset "
                 "proxy/cache locations together. Preserve health checks, host headers, TLS requirements, "
                 "and network access. Validate routing and origin traffic before/after; the source reference "
                 "alone does not prove this hop incurs internet-transfer charges.", "",
                 "   References: " + citations(proxy_findings), ""]
    playlists = [finding for finding in findings if any(link["kind"] == "observed_path"
                 and "playlist" in link["text"] for link in finding["aws_links"])]
    if playlists:
        rows += ["4. **Deduplicate observed playlist requests at the callers.** Reuse an in-flight request for "
                 "the same publication, pagination and authentication state; cancel obsolete fetches. "
                 "Consider a short application cache only after checking freshness and personalization. "
                 "Do not put subscription/user-specific responses in a shared public cache. Validate "
                 "pagination, account changes, and request count per player session.", "",
                 "   References: " + citations(playlists), ""]
    return rows if len(rows) > 4 else []
