# Overall AWS bill retrieval

Account: `{account_id}`
Billing period: `{start_date}` through `{end_date}` (end date is exclusive)

This stage runs locally and does not invoke an OpenAI model.

1. Retrieve bill data grouped by service.
2. Retrieve bill data grouped by region.
3. Retrieve bill data grouped by service and usage type.
4. Calculate each total from every returned group.
5. Return Markdown with the validated total, sorted cost drivers, and data limitations.

Use only facts returned by AWS. Do not include credentials or secrets.
