from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..function_tool import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import AwsToolConfig, client_error_message, create_boto3_session, json_dumps


def get_account_identity_data(config: AwsToolConfig) -> dict[str, Any]:
    """Return the active AWS identity for workflow validation."""
    sts = create_boto3_session(config).client("sts", region_name=config.region)
    return sts.get_caller_identity()


def render_connection_check(
    identity: dict[str, Any],
    expected_account: str | None,
    region: str,
) -> str:
    """Render a deterministic local report without sending identity data to a model."""
    actual_account = str(identity.get("Account", "Unknown"))
    account_matches = not expected_account or expected_account == actual_account
    expected = expected_account or "Not specified"
    status = "Passed" if account_matches else "Failed"

    return f"""# AWS Connection Check

- **Status:** {status}
- **Checked at:** {datetime.now(timezone.utc).isoformat()}
- **AWS region:** `{region}`
- **Expected account:** `{expected}`
- **Authenticated account:** `{actual_account}`
- **Principal ARN:** `{identity.get('Arn', 'Unknown')}`
- **Principal user ID:** `{identity.get('UserId', 'Unknown')}`
- **Respan contacted:** No
- **AWS changes made:** None
"""


def create_auth_tools(config: AwsToolConfig) -> list[Any]:
    """Create AWS auth and account identity tools."""

    @tool
    def get_account_identity() -> str:
        """Return the AWS account identity for the credentials used by this run."""
        try:
            return json_dumps(get_account_identity_data(config))
        except (BotoCoreError, ClientError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [get_account_identity]
