#!/usr/bin/env python3
"""Find evidence connecting AWS load-balancer traffic with repository code.

Run from any directory. Reads experiments/.env by default; see README.md for
permissions, sampling limits, and offline reproduction of the Markdown report.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from traffic_analysis.access_logs import sample_logs
from traffic_analysis.aws_evidence import AwsCollector
from traffic_analysis.common import Redactor, attempt, load_environment, safe_error, save_json, write_private
from traffic_analysis.github_evidence import scan_repository, validate_repo
from traffic_analysis.llm_review import prepare_review, review
from traffic_analysis.report import render_report
from traffic_analysis.source_scan import build_indicators, revalidate_findings

DIRECTORY = Path(__file__).resolve().parent


def positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be positive")
    return number


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=DIRECTORY / ".env")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 4, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 10, 1), help="Exclusive end date")
    parser.add_argument("--regions", nargs="+", default=[], help="Default: all enabled AWS regions")
    parser.add_argument("--repo", action="append", type=validate_repo, help="Repeat to restrict the repository list")
    parser.add_argument("--repos-file", type=Path, default=DIRECTORY / "traffic_analysis/repositories.txt")
    parser.add_argument("--output", type=Path, default=DIRECTORY / "reports/network_traffic_report.md")
    parser.add_argument("--evidence", type=Path, help="Reuse saved JSON; no AWS/GitHub requests")
    parser.add_argument("--refresh-repositories", action="store_true", help="With --evidence, reuse AWS but rescan GitHub")
    parser.add_argument("--skip-aws", action="store_true")
    parser.add_argument("--skip-github", action="store_true")
    parser.add_argument("--no-llm", action="store_true", help="Disable OpenAI; deterministic report still works")
    parser.add_argument("--prepare-llm", action="store_true", help="Write a local request preview; makes no OpenAI call")
    parser.add_argument("--model", help="OpenAI model (default OPENAI_MODEL or gpt-5-mini)")
    parser.add_argument("--log-days", type=positive, default=7)
    parser.add_argument("--max-log-objects", type=int, default=20, help="Per LB; 0 disables S3 sampling")
    parser.add_argument("--max-log-mb", type=positive, default=64, help="Expanded/compressed read limit per LB")
    parser.add_argument("--max-archive-mb", type=positive, default=96)
    parser.add_argument("--max-files", type=positive, default=10000, help="Eligible source files per repository")
    parser.add_argument("--repo-workers", type=positive, default=3, help="Concurrent repository downloads (maximum 6)")
    args = parser.parse_args()
    if args.prepare_llm:
        args.no_llm = True
    today = datetime.now(timezone.utc).date()
    if not args.start < args.end <= today:
        parser.error(f"Require start < end <= current UTC date ({today})")
    if (args.end - args.start).days > 1400:
        parser.error("Maximum metric window is 1400 days")
    if args.max_log_objects < 0:
        parser.error("--max-log-objects cannot be negative")
    if args.repo_workers > 6:
        parser.error("--repo-workers cannot exceed 6")
    return args


def run(args: argparse.Namespace) -> int:
    environment = load_environment(args.env_file)
    redactor = Redactor(environment)
    evidence_path = args.output.with_suffix(".json")
    if args.evidence:
        evidence = json.loads(args.evidence.read_text())
        if not all(field in evidence for field in ["generated_at", "start", "end", "findings", "repositories", "issues"]):
            raise ValueError("Not a traffic-analysis evidence file")
        print("Reusing saved AWS evidence.", flush=True)
        if args.refresh_repositories:
            evidence["repositories"], evidence["findings"] = [], []
            evidence["llm"] = {"status": "not requested for refreshed source evidence"}
            evidence["issues"] = [issue for issue in evidence["issues"] if not issue.startswith(("GitHub ", "OpenAI "))
                                  and issue != "GitHub collection explicitly skipped"]
    else:
        evidence = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
                    "start": str(args.start), "end": str(args.end), "issues": [], "findings": [], "repositories": [],
                    "limits": {"max_files": args.max_files, "max_archive_mb": args.max_archive_mb,
                               "log_days": args.log_days, "max_log_objects": args.max_log_objects,
                               "max_log_mb": args.max_log_mb}}
        if args.skip_aws:
            evidence["aws"] = {"status": "skipped", "load_balancers": [], "billing": []}
            evidence["issues"].append("AWS collection explicitly skipped")
        else:
            print("Collecting AWS billing, load balancers, DNS, CDN and metrics (read only)...", flush=True)
            collector = AwsCollector(environment, args.start, args.end, args.regions, evidence["issues"])
            evidence["aws"] = collector.collect()
            save_json(evidence_path, evidence, redactor)
            log_start = max(args.start, args.end - timedelta(days=args.log_days))
            for balancer in evidence["aws"].get("load_balancers", []):
                print(f"  Access logs: {balancer['name']}", flush=True)
                balancer["access_logs"] = attempt(evidence["issues"], f"S3 logs {balancer['name']}", lambda: sample_logs(
                    collector, balancer, evidence["aws"]["account"], log_start, args.end,
                    args.max_log_objects, args.max_log_mb * 1024 ** 2), {"status": "unavailable", "routes": []})
            save_json(evidence_path, evidence, redactor)
    if not args.evidence or args.refresh_repositories:
        if not args.skip_github:
            repos = args.repo or [line.strip() for line in args.repos_file.read_text().splitlines()
                                  if line.strip() and not line.startswith("#")]
            indicators = build_indicators(evidence["aws"])
            def collect_repo(repo: str) -> dict:
                print(f"Scanning {repo}...", flush=True)
                return attempt(evidence["issues"], f"GitHub {repo}", lambda: scan_repository(
                    repo, environment, indicators, redactor, args.max_files, args.max_archive_mb * 1024 ** 2),
                    {"repo": repo, "status": "unavailable; see coverage gaps", "findings": []})
            with ThreadPoolExecutor(max_workers=args.repo_workers) as executor:
                futures = [executor.submit(collect_repo, repo) for repo in dict.fromkeys(repos)]
                for future in as_completed(futures):
                    result = future.result()
                    findings = result.pop("findings", [])
                    for finding in findings:
                        finding["id"] = f"F{len(evidence['findings']) + 1:04d}"
                        evidence["findings"].append(finding)
                    evidence["repositories"].append(result)
                    print(f"  {result['repo']}: {result['status']}; {result.get('files_scanned', 0)} files; "
                          f"{len(findings)} retained candidates", flush=True)
                    save_json(evidence_path, evidence, redactor)
        else:
            evidence["issues"].append("GitHub collection explicitly skipped")
    # Always save a useful deterministic report before the optional external model call.
    evidence["findings"] = revalidate_findings(evidence["findings"], evidence.get("aws", {}))
    evidence["issues"] = list(dict.fromkeys(evidence["issues"]))
    if args.no_llm:
        evidence["llm"] = {"status": "disabled"}
    elif not environment.get("OPENAI_API_KEY"):
        evidence["llm"] = {"status": "skipped: OPENAI_API_KEY not configured"}
    write_private(args.output, render_report(evidence), redactor)
    if args.prepare_llm:
        preview_path = args.output.with_suffix(".llm-request.json")
        save_json(preview_path, prepare_review(evidence, redactor,
                  args.model or environment.get("OPENAI_MODEL", "gpt-5-mini")), redactor)
        print(f"Local OpenAI request preview (not sent): {preview_path}", flush=True)
    if not args.no_llm and environment.get("OPENAI_API_KEY"):
        print("Requesting one bounded OpenAI review of redacted findings...", flush=True)
        evidence["llm"] = attempt(evidence["issues"], "OpenAI review", lambda: review(
            evidence, environment, redactor, args.model or environment.get("OPENAI_MODEL", "gpt-5-mini")),
            {"status": "unavailable; deterministic report preserved"})
    save_json(evidence_path, evidence, redactor)
    write_private(args.output, render_report(evidence), redactor)
    print(f"Report: {args.output.resolve()}\nEvidence: {evidence_path.resolve()}", flush=True)
    print(f"Coverage gaps: {len(evidence['issues'])}; review the report before drawing conclusions.", flush=True)
    useful = bool(evidence.get("findings") or evidence.get("aws", {}).get("billing")
                  or evidence.get("aws", {}).get("load_balancers"))
    return 0 if useful else 2


def main() -> int:
    args = arguments()
    try:
        return run(args)
    except KeyboardInterrupt:
        print("Interrupted; collected evidence checkpoints remain in the output directory.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Analysis failed: {safe_error(error)}. No credential values or API bodies are logged.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
