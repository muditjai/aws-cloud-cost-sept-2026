# AWS Cloud Cost Agent Tools

This file is the source-of-truth registry for tools the agent is allowed to use. If a needed capability is missing, the agent should use web search to identify the AWS API and append a proposal to `proposed_tools.md`.

## Discovery And Cost Tools

### `read_tools_registry`

Reads this file before the agent makes AWS API calls.

### `get_account_identity`

Calls `sts:GetCallerIdentity` to confirm which AWS account and principal the run is analyzing.

### `get_cost_and_usage`

Calls `ce:GetCostAndUsage` for historical AWS cost and usage data.

Inputs:

- `start`: Inclusive start date in `YYYY-MM-DD`.
- `end`: Exclusive end date in `YYYY-MM-DD`.
- `granularity`: `DAILY` or `MONTHLY`.
- `metrics_csv`: Comma-separated Cost Explorer metrics.
- `group_by_csv`: Comma-separated dimensions such as `SERVICE`, `REGION`, `USAGE_TYPE`, or `OPERATION`.
- `filter_json`: Optional Cost Explorer Expression JSON.

### `get_top_cost_drivers`

Calls `ce:GetCostAndUsage` and ranks grouped cost drivers by metric amount.

Use it for:

- Account-level service rankings with `group_by_csv=SERVICE`.
- Service/SKU approximation with `group_by_csv=SERVICE,USAGE_TYPE`.
- Region rankings with `group_by_csv=REGION`.

### `get_service_cost_breakdown`

Calls `ce:GetCostAndUsage` with a `SERVICE` filter and ranks the service by usage type, operation, region, or other Cost Explorer dimensions.

Default grouping is `USAGE_TYPE,OPERATION`, which is the closest Cost Explorer approximation to SKU-level cost detail available in the current tool set.

### `get_cost_forecast`

Calls `ce:GetCostForecast` for a future period.

### `get_rightsizing_recommendations`

Calls `ce:GetRightsizingRecommendation` for EC2 rightsizing signals.

### `get_savings_plans_recommendations`

Calls `ce:GetSavingsPlansPurchaseRecommendation` for commitment discount opportunities.

### `get_reservation_recommendations`

Calls `ce:GetReservationPurchaseRecommendation` for Reserved Instance opportunities.

## Artifact Tools

### `write_assessment_file`

Writes Markdown under the `assessment/` folder. The agent should write:

- `total-cost.md`
- One Markdown file per top service/SKU driver specialist analysis.
- Any supporting assessment files that make the analysis auditable.

### `record_proposed_tool`

Appends missing tool proposals to `proposed_tools.md`. Use this after web search when Cost Explorer is insufficient for a service-specific diagnosis.

### `stage_change_plan`

Writes candidate optimization actions to `optmization_script/considered_actions.py`.

This does not mutate AWS resources. Every staged action requires human approval before implementation.

## Sub-Agent Tools

### `analyze_service_cost_driver`

Spawns the service/SKU specialist sub-agent. The parent agent should call this once per top service/SKU cost driver selected for the run.
