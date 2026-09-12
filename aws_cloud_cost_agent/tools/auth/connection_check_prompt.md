# AWS connection check

Expected account: `{account_id}`

This stage runs locally and does not invoke the Respan API.

1. Call AWS STS `GetCallerIdentity`.
2. Confirm whether authentication succeeded and whether the returned account is `{account_id}`.
3. Return Markdown with: status, account ID, principal ARN, region, and whether Respan was contacted.

Do not include credentials or secrets.
