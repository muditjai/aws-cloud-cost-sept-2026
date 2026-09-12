# Amazon RDS cost analysis

Account: `{account_id}`
Billing period: `{start_date}` through `{end_date}` (end date is exclusive)
Focus usage type: `{sku}`
Observed focus cost: `{cost}`

1. Read the tool registry.
2. Retrieve exact RDS component costs and copy exact rows without model arithmetic.
3. Attempt resource-level cost retrieval and state its exact availability window.
4. Inventory RDS instances and clusters, including class, engine, storage, Multi-AZ, and Aurora Serverless v2 settings.
5. Retrieve per-instance CPU, connections, memory, and serverless capacity metrics.
6. Retrieve deterministic per-instance compute and GP3 cost attribution and copy its dollar estimates without model arithmetic.
7. Map remaining cluster-level components only where evidence supports it.
8. Keep exact AWS charges separate from inferred resource attribution.
9. Return Markdown with total cost, component and region tables, per-instance cost estimates, inventory, utilization, likely cost drivers, confidence, and missing data.

Do not recommend or perform changes in this step. Do not include credentials or secrets.
