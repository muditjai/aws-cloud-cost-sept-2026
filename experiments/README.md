# Load balancer traffic investigation

`network_traffic_cause.py` connects AWS billing/inventory/traffic evidence with code
in the 46 repositories in `traffic_analysis/repositories.txt`. It writes a Markdown
report and a companion JSON evidence file. It never changes AWS configuration,
executes downloaded code, commits, or pushes to GitHub.

## Run

Python 3.10 or later:

```bash
python3 -m venv experiments/.venv
experiments/.venv/bin/python -m pip install -r experiments/requirements.txt
experiments/.venv/bin/python experiments/network_traffic_cause.py
```

The script resolves paths relative to itself, so it also runs outside the project
directory. The existing `experiments/.env` is loaded without printing its values.
Values in that explicitly selected file override the process environment; dotenv
interpolation is disabled to preserve literal credential characters.

Supported variables:

```dotenv
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...             # optional, for temporary credentials
AWS_REGION=us-east-1
ORG_PAT=...                       # instaread-co repositories
PERSONAL_PAT=...                  # rahulcee and rahuligan repositories
OPENAI_API_KEY=...                # optional
OPENAI_MODEL=gpt-5-mini           # optional; --model overrides this
```

`GITHUB_TOKEN` or `GIT_TOKEN` is a fallback when the owner-specific token is absent.
Without explicit AWS keys, the normal boto3 credential chain is used; `AWS_PROFILE`
is also supported. GitHub tokens need read access to repository contents/metadata,
including the organization's SSO authorization where applicable. A 404 can mean
that the repository is private and inaccessible; it does not prove it is absent.

Default output:

- `experiments/reports/network_traffic_report.md`
- `experiments/reports/network_traffic_report.json`

The output directory and virtual environment are gitignored. Reports contain
private infrastructure names and redacted source excerpts; they are written with
mode `0600`. Do not publish them without reviewing their contents. Secret
redaction is best effort, not a substitute for treating the reports as private.

## Useful options

```bash
# Purely deterministic investigation: no source excerpts sent to OpenAI.
experiments/.venv/bin/python experiments/network_traffic_cause.py --no-llm

# Narrow the time range, AWS regions, and repositories.
experiments/.venv/bin/python experiments/network_traffic_cause.py \
  --start 2026-09-01 --end 2026-10-01 --regions us-east-1 \
  --repo instaread-co/terraform-aws --repo rahulcee/instaread-webservice-node

# Rebuild a report offline from its JSON evidence, with no API requests.
experiments/.venv/bin/python experiments/network_traffic_cause.py \
  --evidence experiments/reports/network_traffic_report.json --no-llm

# Inspect the exact redacted model request locally before sending anything.
experiments/.venv/bin/python experiments/network_traffic_cause.py \
  --evidence experiments/reports/network_traffic_report.json --prepare-llm

# Add one OpenAI review to existing evidence, without repeating AWS/GitHub calls.
experiments/.venv/bin/python experiments/network_traffic_cause.py \
  --evidence experiments/reports/network_traffic_report.json

# Reuse AWS collection, but rescan the repository list with the current rules.
experiments/.venv/bin/python experiments/network_traffic_cause.py \
  --evidence experiments/reports/network_traffic_report.json --refresh-repositories

# Skip log reads or expand a bounded sample.
experiments/.venv/bin/python experiments/network_traffic_cause.py --max-log-objects 0
experiments/.venv/bin/python experiments/network_traffic_cause.py \
  --log-days 14 --max-log-objects 100 --max-log-mb 128
```

Defaults analyze April 1 through October 1, 2026 (end exclusive), matching the
supplied bill. Dates cannot be in the future. `--skip-aws`, `--skip-github`,
`--repos-file`, `--max-files`, `--max-archive-mb`, `--env-file`, and `--output`
are also available. `--repo-workers` bounds concurrent GitHub scans (default 3,
maximum 6). `--evidence` reuses the saved collection period, regardless
of live-collection date flags. It does not resume an interrupted repository scan.

Exit codes: `0` means useful evidence was collected, **not complete coverage**;
`2` means the report contains no live AWS/code evidence; `1` means a fatal local
error; `130` means interrupted. Read the coverage section even after exit `0`.
JSON is checkpointed after AWS collection and each repository.

## How attribution works

1. Cost Explorer queries the authenticated account, grouped by service and usage
   type, excluding credits/refunds. Costs use `Decimal`. Usage quantities retain
   their units and are not added across incompatible units. API pagination is
   supported even on botocore versions missing CE paginator metadata.
2. All enabled regions are checked for ALB/NLB/GWLB and Classic ELB resources.
   Listeners, safe routing summaries, target groups, DNS aliases, CloudFront
   origins/behaviors, and daily CloudWatch sums establish the live topology.
3. Existing S3 ALB/Classic access logs are sampled from the last seven days of the
   requested period, up to 20 objects and 64 MiB per load balancer. Rows must match
   the exact load balancer and time window. Query strings and client IPs are not
   retained. Routes are ranked by response bytes, with status counts and sample
   coverage. NLB TLS logs cannot establish HTTP route bytes and are not parsed as
   ALB logs. CloudWatch/Firehose-delivered access logs are not collected.
4. GitHub default branches are pinned to commit SHAs and downloaded as bounded
   archives. Very large archives fall back to at most 180 prioritized Git blob
   reads, with tree truncation and omitted files reported. No archive is extracted to disk. Symlinks, traversal paths, secret
   files, dependencies, generated/minified files, binary data, and oversized
   files are excluded. Rules flag media streaming, cache bypasses, preloading,
   buffering, polling, and infrastructure; live hosts/routes strengthen matches.
   Each retained candidate includes a commit-specific path/line link and excerpt.
5. When an OpenAI key is configured, one Responses API call reviews a diverse set
   of up to 60 redacted candidates and bounded AWS evidence. `store=false` is set.
   Repository content is treated as untrusted data and the model has no tools.
   Structured output and local validation reject unknown evidence IDs. The model
   suggests conditional changes and tests; it does not calculate savings or
   establish runtime causality. API failure leaves the deterministic report intact.

Cost Explorer, CloudWatch, S3 reads, GitHub downloads, and optional OpenAI calls can
incur normal service charges. The code sets timeouts, bounded retries, archive/log
size limits and one model call; it does not perform an unbounded agent loop.

## Read permissions

The collector uses these AWS actions; optional discovery failures are recorded
and do not suppress already collected evidence:

```text
sts:GetCallerIdentity
ce:GetCostAndUsage
ec2:DescribeRegions
elasticloadbalancing:DescribeLoadBalancers
elasticloadbalancing:DescribeLoadBalancerAttributes
elasticloadbalancing:DescribeListeners
elasticloadbalancing:DescribeRules
elasticloadbalancing:DescribeTargetGroups
cloudwatch:GetMetricStatistics
route53:ListHostedZones
route53:ListResourceRecordSets
cloudfront:ListDistributions
s3:ListBucket                  (existing log buckets/prefixes)
s3:GetObject                   (existing log objects)
kms:Decrypt                    (only if required by an existing log object's KMS key)
```

These are the actions used, not a blanket IAM policy. Scope S3/KMS access to the
actual log locations. The script does not grant permissions or enable logging.

## Interpretation limits

`DataTransfer-Out-Bytes` is not the same as ALB LCU charges, bidirectional
`ProcessedBytes`, or sampled application `sent_bytes`. Account/service billing
cannot identify a single load balancer or function by itself. The report keeps
those layers separate; it does not allocate dollars by sampled byte shares.

Current inventory can miss deleted resources. Default-branch code may differ from
deployed code during the bill period. Missing datapoints are not zero usage. A
bounded latest-log sample is not representative monthly traffic. Disabled logs
cannot be reconstructed retrospectively. CDN delivery still incurs viewer costs;
a CDN recommendation is not a promise that the entire transfer bill disappears.

The scan is intentionally bounded: 96 MiB compressed / 512 MiB expanded per repo,
10,000 eligible files, 512 KiB per file, six matches per rule per file, and 150
retained candidates per repo with at most eight per file. The report displays 45
diverse candidates; all retained findings are in JSON. History, submodules and
Git LFS content are not inspected. Increase limits or target specific repos when
the coverage table identifies a gap.

## Offline tests

```bash
PYTHONPATH=experiments experiments/.venv/bin/python -m unittest discover -s experiments/tests -v
```

Tests cover ALB/Classic field offsets, time/resource filtering, malformed log
records, secret/URL redaction, archive traversal and symlink exclusion, token
selection, AWS DNS/CDN correlation, Cost Explorer pagination/account scoping, and
rejection of invented model citations. They make no external API calls.
