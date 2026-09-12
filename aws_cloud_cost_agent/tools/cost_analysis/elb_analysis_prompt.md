# Elastic Load Balancing cost analysis

Account: `{account_id}`
Billing period: `{start_date}` through `{end_date}` (end date is exclusive)
Focus usage type: `{sku}`
Observed focus cost: `{cost}`

1. Read the tool registry.
2. Retrieve exact ELB component costs and verify their total.
   Copy exact component rows from the tool; do not combine rows or perform model arithmetic.
3. Attempt resource-level costs and clearly state the returned date window and whether AWS has enabled the data.
4. Inventory load balancers, listeners, target groups, and registered targets in regions with ELB spend.
5. Retrieve deterministic per-load-balancer cost attribution and report its estimated transfer, LCU, and combined variable cost columns.
6. Retrieve raw utilization only if needed to explain the deterministic attribution.
7. Separate exact AWS charges from metric-based attribution estimates. Never present an estimate as an invoice line.
8. Explain that registered EC2 targets are dependencies whose compute cost is outside the ELB service bill.
9. Explain the focus usage type in the context of the complete ELB bill.
10. Return Markdown with total ELB cost, component table, region table, per-load-balancer dollar attribution, inventory mapping, confidence, and missing permissions/data.

Do not recommend or perform changes in this step. Do not include credentials or secrets.
