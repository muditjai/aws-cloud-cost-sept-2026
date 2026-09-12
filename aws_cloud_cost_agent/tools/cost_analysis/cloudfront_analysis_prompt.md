# Amazon CloudFront cost analysis

Account: `{account_id}`
Billing period: `{start_date}` through `{end_date}` (end date is exclusive)
Focus usage type: `{sku}`
Observed focus cost: `{cost}`

1. Read the tool registry.
2. Retrieve exact CloudFront component costs and copy exact rows without model arithmetic.
3. Attempt resource-level costs and clearly state whether AWS exposes them.
4. Inventory distributions, origins, price classes, cache behavior counts, compression, and enabled status.
5. Retrieve distribution request, byte, cache-hit, and error metrics.
6. Retrieve deterministic per-distribution request and transfer cost attribution.
7. Separate exact AWS charges from metric-based distribution estimates.
8. Return Markdown with total cost, component table, geographic drivers, distribution estimates, configuration mapping, confidence, and missing data.

Do not recommend or perform changes in this step. Do not include credentials or secrets.
