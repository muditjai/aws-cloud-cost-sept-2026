# AWS Cloud Cost Agent

A small Python agent using Respan's OpenAI-compatible API to read AWS billing data, analyze top service/SKU cost drivers, and produce cost recommendations.

The agent is read-only. It does not modify AWS resources.

## Structure

```text
aws_cloud_cost_agent/
├── cli.py
├── web.py
├── web_assets/
├── steps.py
├── workflow.py
├── agent.py
└── tools/
    ├── tools_main.py
    ├── tools.md
    ├── proposed_tools.md
    ├── auth/
    │   ├── aws_auth.py
    │   └── connection_check_prompt.md
    ├── bill_read/
    │   ├── aws_billing.py
    │   └── overall_bill_prompt.md
    ├── cost_analysis/
    │   ├── cloudfront.py
    │   ├── cloudfront_analysis_prompt.md
    │   ├── elb.py
    │   ├── elb_analysis_prompt.md
    │   ├── per_technology.py
    │   ├── rds.py
    │   ├── rds_analysis_prompt.md
    │   ├── service_costs.py
    │   └── service_sku_analysis_prompt.md
    └── cost_recommendation/
        ├── per_technology_recommendations.py
        └── service_sku_recommendation_prompt.md

output_artifact/
```

`tools_main.py` imports each tool group. Every workflow step has one prompt beside its Python tools. The service analysis and recommendation prompts are rendered and run separately for each of the five highest-cost service/SKU pairs.

## Setup

```bash
cd /home/muditjai/src/aws-cloud-cost-sept-2026
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The CLI automatically loads a local `.env` file. AWS credentials are required for every step:

```bash
AWS_ACCESS_KEY_ID=<aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<aws-secret-access-key>
AWS_REGION=us-east-1
```

`RESPAN_API_KEY` is required for service analysis and recommendation steps. The
`connection-check` and `overall-bill` steps query AWS and calculate their reports
locally without contacting Respan.

```bash
RESPAN_API_KEY=<respan-api-key>
```

Optional values:

```bash
AWS_SESSION_TOKEN=<temporary-session-token>
AWS_PROFILE=<aws-profile-name>
AWS_ACCOUNT_ID=<expected-account-id>
```

The Respan integration uses the OpenAI-compatible Chat Completions function-call
format at `https://api.respan.ai/api/` with model `openai/gpt-6-astra`. It does
not currently expose a web-search tool, so recommendation reports must not claim
current web research.

## CLI

The CLI intentionally exposes only account, date, and step selection:

```bash
python3 -m aws_cloud_cost_agent \
  --aws-account 472186642949 \
  --start-date 2026-08-01 \
  --end-date 2026-09-01 \
  --steps connection-check overall-bill service-analysis recommendations
```

Running without arguments executes every step for the last 30 days:

```bash
python3 -m aws_cloud_cost_agent
```

Available steps:

- `connection-check`
- `overall-bill`
- `service-analysis`
- `recommendations`

## Local web interface

Start the localhost-only wrapper:

```bash
aws-cloud-cost-web
```

Then open `http://127.0.0.1:8765`. The page runs selected workflow steps in the
background and renders Markdown files from `output_artifact/`. AWS and Respan
credentials remain server-side and are never included in the page.

## Output

Each selected step writes Markdown under `output_artifact/`:

```text
output_artifact/
├── connection_check_2026-09-12.md
├── overall_bill_data_2026-08-13_2026-09-12.md
├── service_sku_analysis_<service>_<sku>_<start>_<end>.md
└── recommendations_<service>_<sku>_<start>_<end>.md
```

The analysis and recommendation steps produce one file per top service/SKU pair. Recommendation files show before state, proposed after state, estimated savings, validation, rollback, and approval requirements.

## Tool registry

[tools.md](aws_cloud_cost_agent/tools/tools.md) lists implemented tools. When an agent needs an unavailable AWS API, it records the missing capability in [proposed_tools.md](aws_cloud_cost_agent/tools/proposed_tools.md).

## IAM permissions

Use read-only access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetRightsizingRecommendation",
        "ce:GetSavingsPlansPurchaseRecommendation",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```
