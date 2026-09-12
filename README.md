# AWS Cloud Cost Agent - September 2026

Standalone Python OpenAI Agents SDK project for AWS cost analysis. It calls AWS APIs, summarizes spend, spawns specialist sub-agents for top service/SKU drivers, proposes optimization ideas, and leaves a controlled path for future approved remediation tools.

## Current Behavior

- Reads AWS account identity with STS.
- Accepts AWS access key credentials directly or through the standard AWS SDK credential chain.
- Reads historical AWS spend with Cost Explorer.
- Reads `tools.md` before making exploratory AWS calls.
- Groups spend by service, service/SKU approximation, region, linked account, usage type, operation, purchase type, instance type, or availability zone.
- Fetches AWS forecast data.
- Fetches EC2 rightsizing, Savings Plans, and Reserved Instance purchase recommendations where available.
- Uses web search and writes missing tool proposals to `proposed_tools.md` when the available tools are insufficient.
- Spawns a service/SKU specialist sub-agent for each selected top cost driver.
- Produces Markdown assessment files under `assessment/`.
- Stages proposed change plans for review in `optmization_script/considered_actions.py`.
- Does not mutate AWS resources.

## Dependencies

- `openai-agents`: OpenAI Agents SDK runtime.
- `boto3`: AWS SDK for Python.

These are intentionally scoped to agent orchestration and read-only AWS cost discovery.

## Setup

```bash
cd /home/muditjai/src/aws-cloud-cost-sept-2026
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Required environment:

```bash
export OPENAI_API_KEY=<openai-api-key>
```

AWS credentials can be supplied either through environment variables:

```bash
export AWS_ACCESS_KEY_ID=<aws-access-key-id>
export AWS_SECRET_ACCESS_KEY=<aws-secret-access-key>
export AWS_SESSION_TOKEN=<optional-session-token>
```

or through the default AWS SDK credential chain:

```bash
export AWS_PROFILE=<aws-profile-name>
```

Environment variables are usually safer than passing secrets as CLI args because shell history may capture CLI args.

Optional environment:

```bash
export OPENAI_MODEL=<model-name>
```

If `OPENAI_MODEL` is unset, the OpenAI Agents SDK default model is used.

## IAM Permissions

Use read-only permissions for analysis:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetDimensionValues",
        "ce:GetRightsizingRecommendation",
        "ce:GetSavingsPlansPurchaseRecommendation",
        "ce:GetReservationPurchaseRecommendation",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Do not grant write permissions until a specific mutating tool is implemented, reviewed, and approved.

## Usage

Analyze the last 30 days:

```bash
python -m aws_cloud_cost_agent
```

Analyze with explicit access key credentials:

```bash
python -m aws_cloud_cost_agent \
  --aws-access-key-id <aws-access-key-id> \
  --aws-secret-access-key <aws-secret-access-key>
```

Analyze a specific period:

```bash
python -m aws_cloud_cost_agent --start 2026-09-01 --end 2026-10-01
```

Group by a different Cost Explorer dimension:

```bash
python -m aws_cloud_cost_agent --group-by REGION
```

Write the final report to a local markdown file:

```bash
python -m aws_cloud_cost_agent --out reports/aws-cost-review.md
```

Analyze more or fewer top drivers with service/SKU specialist sub-agents:

```bash
python -m aws_cloud_cost_agent --top-drivers 8
```

Default generated artifacts:

```text
assessment/
├── final-report.md
├── total-cost.md
└── <service-or-sku>.md

optmization_script/
└── considered_actions.py

proposed_tools.md
```

Show all CLI options:

```bash
python -m aws_cloud_cost_agent --help
```

## Future Remediation Path

Future AWS mutations should be implemented as narrow service-specific tools. Each tool should require:

- A prior report recommendation ID.
- Exact account, region, service, and resource IDs.
- An expected savings estimate.
- A validation plan.
- A rollback plan.
- `--apply`.
- `AWS_COST_AGENT_ENABLE_MUTATIONS=true`.

The default agent prompt must continue to prefer recommendations and staged change plans over automatic execution.
