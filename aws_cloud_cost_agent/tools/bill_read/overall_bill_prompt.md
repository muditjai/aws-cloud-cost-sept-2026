# Overall AWS bill retrieval

Account: `{account_id}`
Billing period: `{start_date}` through `{end_date}` (end date is exclusive)

1. Read the tool registry.
2. Retrieve bill data grouped by service.
3. Retrieve bill data grouped by region.
4. Retrieve bill data grouped by service and usage type.
5. Return Markdown with total cost, top services, top regions, top service/SKU pairs, and data limitations.

Use only facts returned by AWS. Do not include credentials or secrets.
