# AWS connection check

Expected account: `{account_id}`

1. Read the tool registry.
2. Call the AWS identity tool.
3. Confirm whether authentication succeeded and whether the returned account is `{account_id}`.
4. Return Markdown with: status, account ID, principal ARN, and any access error.

Do not include credentials or secrets.
