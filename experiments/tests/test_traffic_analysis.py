"""Offline behavioral tests: attribution, pagination, secret handling, and limits."""

import io
import json
import tarfile
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
from botocore.stub import Stubber

from traffic_analysis.access_logs import aggregate_lines, parse_log
from traffic_analysis.action_plan import action_plan
from traffic_analysis.aws_evidence import AwsCollector, link_domains, summarize_actions
from traffic_analysis.common import Redactor, load_environment, save_json
from traffic_analysis.github_evidence import scan_archive, scan_tree, token_for, validate_repo
from traffic_analysis.llm_review import add_review_notes, prepare_review, submit_review, validate_review
from traffic_analysis.report import render_report
from traffic_analysis.source_scan import eligible_source, indicator_matches, scan_source

ALB = ('https 2026-09-30T12:00:00.000000Z app/media/abc 1.2.3.4:1234 10.0.0.2:80 '
       '0.001 0.002 0.001 206 206 120 2048 '
       '"GET https://media.example.com/audio/123.mp3?token=secret HTTP/1.1" '
       '"Browser Agent" TLS_AES_128_GCM_SHA256 TLSv1.3 '
       'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/media/abc "trace"')
CLB = ('2026-09-30T12:00:00.000000Z classic-media 1.2.3.4:1234 10.0.0.2:80 '
       '0.001 0.002 0.001 200 200 120 4096 '
       '"GET https://media.example.com/audio/test.mp3 HTTP/1.1" "Browser Agent" TLS TLSv1.2')


class LogTests(unittest.TestCase):
    def test_alb_fields_query_removal_and_partial_content(self):
        row = parse_log(ALB)
        self.assertEqual(row["sent_bytes"], 2048)
        self.assertEqual(row["status"], "206")
        self.assertEqual(row["path"], "/audio/{id}.mp3")
        self.assertNotIn("token", json.dumps(row, default=str))
        self.assertNotIn("1.2.3.4", json.dumps(row, default=str))

    def test_classic_field_offsets(self):
        row = parse_log(CLB, classic=True)
        self.assertEqual((row["sent_bytes"], row["status"], row["balancer_id"]), (4096, "200", "classic-media"))

    def test_mixed_lb_and_out_of_window_rows_do_not_contaminate_totals(self):
        summary = aggregate_lines([ALB, ALB, ALB.replace("app/media/abc", "app/other/def"),
                                   ALB.replace("2026-09-30", "2026-10-01"), "broken"],
                                  {"name": "media", "type": "application", "arn": "arn:loadbalancer/app/media/abc"},
                                  date(2026, 9, 1), date(2026, 10, 1))
        self.assertEqual(summary["routes"][0]["requests"], 2)
        self.assertEqual(summary["routes"][0]["sent_bytes"], 4096)
        self.assertEqual(summary["excluded_lines"], 2)
        self.assertEqual(summary["malformed_lines"], 1)

    def test_nlb_tls_records_are_not_misinterpreted_as_http(self):
        self.assertIsNone(parse_log("tls 2.0 2026-09-30T12:00:00Z net/media/abc many other fields"))


class SecurityAndSourceTests(unittest.TestCase):
    def test_environment_does_not_expand_dollar_sequences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('OPENAI_API_KEY="literal-${HOME}"\n')
            self.assertEqual(load_environment(path)["OPENAI_API_KEY"], "literal-${HOME}")

    def test_credentials_and_url_queries_redacted_without_corrupting_json(self):
        redactor = Redactor({"ORG_PAT": "sensitive-secret-value"})
        snippet = 'const url = "https://example.com/audio?token=sensitive-secret-value";'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            save_json(path, {"snippet": redactor.clean(snippet)}, redactor)
            result = json.loads(path.read_text())
            self.assertNotIn("sensitive-secret-value", result["snippet"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_secrets_generated_files_and_traversal_are_excluded(self):
        for path in [".env", "src/.env.production", "a/credentials.json", "node_modules/a.js",
                     "src/player.min.js", "package-lock.json", "../../src/a.py", "/etc/config.json"]:
            self.assertFalse(eligible_source(path), path)
        self.assertTrue(eligible_source("routes/audio.py"))

    def test_tokens_select_correct_owner(self):
        environment = {"ORG_PAT": "organization", "PERSONAL_PAT": "personal"}
        self.assertEqual(token_for("instaread-co/player", environment), "organization")
        self.assertEqual(token_for("rahuligan/player", environment), "personal")
        self.assertEqual(validate_repo("https://github.com/instaread-co/player.git"), "instaread-co/player")
        with self.assertRaises(ValueError):
            validate_repo("https://evil.example/owner/repo")

    def test_source_correlates_observed_host_and_preserves_commit_citation(self):
        source = 'const origin = "https://media.example.com";\nres.sendFile(audioPath);\n'
        findings = scan_source("org/repo", "abc123", "server.js", source,
                               [{"text": "media.example.com", "balancer": "media", "kind": "direct_host"}], Redactor({}))
        finding = next(row for row in findings if row["rule"] == "media_proxy")
        self.assertEqual(finding["line"], 2)
        self.assertIn("/abc123/server.js#L2", finding["url"])
        self.assertEqual(finding["aws_links"][0]["balancer"], "media")
        self.assertIn("unconfirmed", finding["confidence"])

    def test_parent_domain_does_not_match_other_subdomains(self):
        indicator = {"text": "instaread.co", "kind": "direct_host"}
        self.assertFalse(indicator_matches(indicator, 'fetch("https://player.instaread.co/player")'))
        self.assertTrue(indicator_matches(indicator, 'fetch("https://instaread.co/player")'))

    def test_commented_out_handlers_do_not_become_active_code_findings(self):
        self.assertEqual(scan_source("a/b", "sha", "audio.py", '# return FileResponse(path)', [], Redactor({})), [])

    def test_observed_http_route_does_not_match_module_import(self):
        indicator = {"text": "/player", "kind": "observed_path"}
        self.assertFalse(indicator_matches(indicator, 'import Player from "@/types/player"'))
        self.assertTrue(indicator_matches(indicator, 'app.get("/player", handlePlayer)'))
        self.assertTrue(indicator_matches(indicator, 'fetch("https://player.example.com/player?a=1")'))
        indicator["host"] = "player.example.com"
        self.assertFalse(indicator_matches(indicator, 'fetch("https://other.example.com/player")'))

    def test_archive_ignores_links_and_secrets_without_extracting(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, content in [("root/routes/audio.py", b"return FileResponse(path)"),
                                  ("root/.env", b"PAT=secret"), ("root/../../escape.py", b"send_file(path)")]:
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            link = tarfile.TarInfo("root/link.py")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            archive.addfile(link)
        result = scan_archive(buffer.getvalue(), "org/repo", "abc", [], Redactor({}), 100)
        self.assertEqual(result["files_scanned"], 1)
        self.assertEqual(result["findings"][0]["path"], "routes/audio.py")

    def test_llm_cannot_cite_unknown_evidence(self):
        action = {field: "test" for field in ["title", "mechanism", "proposed_change", "verification", "uncertainty"]}
        action["evidence_ids"] = ["invented"]
        with self.assertRaises(ValueError):
            validate_review({"actions": [action]}, {"F0001"})
        action["evidence_ids"] = ["F0001"]
        self.assertEqual(len(validate_review({"actions": [action]}, {"F0001"})["actions"]), 1)

    def test_large_repo_tree_fallback_reports_truncation_and_blob_limit(self):
        tree = {"truncated": True, "tree": [
            {"type": "blob", "mode": "100644", "path": "server.js", "sha": "a", "size": 30},
            {"type": "blob", "mode": "100644", "path": "other.js", "sha": "b", "size": 30},
            {"type": "blob", "mode": "120000", "path": "secret-link.js", "sha": "c", "size": 30}]}
        import base64
        blob = {"encoding": "base64", "content": base64.b64encode(b"res.sendFile(audioPath);").decode()}
        with patch("traffic_analysis.github_evidence.github_json", side_effect=[tree, blob]) as request:
            result = scan_tree(None, "org/repo", "abc", {}, [], Redactor({}), 1)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(result["files_scanned"], 1)
        self.assertEqual(result["findings"][0]["path"], "server.js")
        self.assertIn("truncated", result["limitations"][1])

    def test_incomplete_llm_response_keeps_usage_and_explicit_reason(self):
        response = MagicMock()
        response.json.return_value = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"},
                                      "usage": {"output_tokens": 12}}
        response.__enter__.return_value = response
        request = {"model": "example-model", "input": json.dumps({"findings": [{"id": "F0001"}]})}
        with patch("traffic_analysis.llm_review.requests.post", return_value=response) as call:
            result = submit_review(request, {"OPENAI_API_KEY": "test-credential"}, Redactor({}))
        self.assertIn("max_output_tokens", result["status"])
        self.assertEqual(result["usage"]["output_tokens"], 12)
        self.assertEqual(call.call_count, 1)
        self.assertNotIn("actions", result)

    def test_llm_schema_only_allows_evidence_ids_actually_sent(self):
        request = prepare_review({"findings": [{"id": "F0042", "repo": "org/repo", "path": "server.py",
                                 "score": 8, "rule": "media_proxy", "snippet": "1: return FileResponse(path)"}],
                                 "issues": [], "aws": {"load_balancers": []}}, Redactor({}), "example-model")
        allowed = request["text"]["format"]["schema"]["properties"]["actions"]["items"]["properties"]["evidence_ids"]["items"]["enum"]
        self.assertEqual(allowed, ["F0042"])
        self.assertFalse(request["store"])

    def test_unsound_model_recipes_get_explicit_review_notes(self):
        result = add_review_notes({"actions": [{"proposed_change": "proxy_set_header Accept-Ranges bytes;"},
                                              {"proposed_change": "Make partners.csv public unless upstream marks it private."}]})
        self.assertIn("Do not apply", result["actions"][0]["review_notes"][0])
        self.assertIn("Keep no-store", result["actions"][1]["review_notes"][0])

    def test_llm_output_is_validated_before_secret_redaction(self):
        action = {field: "Review snippet" for field in ["title", "mechanism", "proposed_change", "verification", "uncertainty"]}
        action["proposed_change"] = 'Remove the literal "private-example-token" from this snippet.'
        action["evidence_ids"] = ["F0001"]
        response = MagicMock()
        response.json.return_value = {"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps({"actions": [action]})}]}]}
        response.__enter__.return_value = response
        request = {"model": "example-model", "input": json.dumps({"findings": [{"id": "F0001"}]})}
        with patch("traffic_analysis.llm_review.requests.post", return_value=response):
            result = submit_review(request, {"OPENAI_API_KEY": "test-credential"},
                                   Redactor({"ORG_PAT": "private-example-token"}))
        self.assertEqual(result["status"], "completed")
        self.assertNotIn("private-example-token", json.dumps(result))


class AwsTests(unittest.TestCase):
    def test_authentication_listener_secrets_never_persist(self):
        result = summarize_actions([{"Type": "authenticate-oidc", "AuthenticateOidcConfig": {"ClientSecret": "hidden"}}])
        self.assertNotIn("hidden", json.dumps(result))

    def test_dns_chains_and_cloudfront_origin_map(self):
        balancer = {"name": "media", "dns": "media.elb.amazonaws.com", "rules": []}
        link_domains([balancer], [{"name": "origin.example.com", "targets": ["media.elb.amazonaws.com"]},
                                  {"name": "api.example.com", "targets": ["origin.example.com"]}],
                     [{"id": "CDN", "domain": "test.cloudfront.net", "aliases": ["cdn.example.com"],
                       "origins": [{"domain": "origin.example.com"}]}])
        self.assertIn("api.example.com", balancer["direct_domains"])
        self.assertEqual(balancer["cloudfront_ids"], ["CDN"])
        self.assertNotIn("cdn.example.com", balancer["direct_domains"])

    def test_cost_explorer_pagination_filters_account_and_keeps_units(self):
        collector = AwsCollector({"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing"},
                                 date(2026, 4, 1), date(2026, 10, 1), [], [])
        client = collector.client("ce", "us-east-1")
        response = {"ResultsByTime": [{"TimePeriod": {"Start": "2026-04-01", "End": "2026-05-01"},
                   "Estimated": False, "Groups": [{"Keys": ["Amazon Elastic Load Balancing", "LCUUsage"],
                   "Metrics": {"UnblendedCost": {"Amount": "12.30", "Unit": "USD"},
                               "UsageQuantity": {"Amount": "123", "Unit": "GB"}}}]}]}
        expected = {"TimePeriod": {"Start": "2026-04-01", "End": "2026-10-01"}, "Granularity": "MONTHLY",
                    "Metrics": ["UnblendedCost", "UsageQuantity"],
                    "Filter": {"And": [{"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": ["123456789012"]}},
                                        {"Not": {"Dimensions": {"Key": "RECORD_TYPE", "Values": ["Credit", "Refund"]}}}]},
                    "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}, {"Type": "DIMENSION", "Key": "USAGE_TYPE"}]}
        with Stubber(client) as stub:
            stub.add_response("get_cost_and_usage", {**response, "NextPageToken": "next"}, expected)
            stub.add_response("get_cost_and_usage", response, {**expected, "NextPageToken": "next"})
            rows = collector.billing("123456789012")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["unit"], "GB")

    def test_report_preserves_unknown_metrics_and_does_not_allocate_dollars(self):
        report = render_report({"generated_at": "now", "start": "2026-04-01", "end": "2026-10-01",
                                "issues": ["CloudWatch: AccessDenied"], "repositories": [], "findings": [],
                                "aws": {"billing": [], "load_balancers": []}})
        self.assertIn("$8,960.49", report)
        self.assertIn("no per-load-balancer dollar allocation", report)
        self.assertIn("AccessDenied", report)

    def test_action_plan_requires_observed_assets_or_a_real_upstream_directive(self):
        evidence = {"findings": [{"id": "F0001", "repo": "org/repo", "path": "nginx.conf", "line": 2,
                     "url": "https://github.com/org/repo/blob/sha/nginx.conf#L2", "score": 10,
                     "snippet": "2: # Documentation mentions example.elb.amazonaws.com", "aws_links": []}],
                    "aws": {"load_balancers": [{"name": "example", "dns": "example.elb.amazonaws.com", "scheme": "internet-facing"}]}}
        self.assertEqual(action_plan(evidence), [])
        evidence["findings"][0]["snippet"] = "2: server example.elb.amazonaws.com;"
        plan = "\n".join(action_plan(evidence))
        self.assertIn("internal endpoint", plan)
        self.assertIn("does not prove", plan)


if __name__ == "__main__":
    unittest.main()
