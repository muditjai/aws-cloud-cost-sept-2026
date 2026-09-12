# AWS service/SKU in-depth analysis

Account: `{account_id}`
Billing period: `{start_date}` through `{end_date}` (end date is exclusive)
Service: `{service}`
SKU or usage type: `{sku}`
Observed cost: `{cost}`

1. Read the tool registry.
2. Retrieve the service breakdown by usage type, operation, and region.
3. Analyze what is driving this service/SKU cost.
4. Return Markdown with cost facts, usage drivers, anomalies, likely waste, confidence, and missing data.
5. If deeper analysis needs a tool that is not available, record it with the proposed-tool tool.

Do not recommend or perform changes in this step. Do not include credentials or secrets.
