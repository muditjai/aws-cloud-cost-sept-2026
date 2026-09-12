# AWS service/SKU cost recommendations

Account: `{account_id}`
Billing period: `{start_date}` through `{end_date}` (end date is exclusive)
Service: `{service}`
SKU or usage type: `{sku}`
Observed cost: `{cost}`

1. Read the tool registry.
2. Retrieve the current service/SKU cost breakdown.
3. Use relevant AWS-native recommendation tools.
4. Use official AWS web sources when the implemented tools do not cover this technology.
5. Return Markdown with a separate section for each recommendation containing:
   - Before state and cost
   - Proposed after state and estimated cost
   - Estimated savings and confidence
   - Exact implementation steps
   - Functional and SLA validation
   - Rollback plan
   - Human approval requirement
6. If a required AWS API tool is missing, record it with the proposed-tool tool.

Do not perform changes. Clearly label assumptions. Do not include credentials or secrets.
