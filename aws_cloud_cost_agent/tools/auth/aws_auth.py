from __future__ import annotations

from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import AwsToolConfig, client_error_message, create_boto3_session, json_dumps


def get_account_identity_data(config: AwsToolConfig) -> dict[str, Any]:
    """Return the active AWS identity for workflow validation."""
    sts = create_boto3_session(config).client("sts", region_name=config.region)
    return sts.get_caller_identity()


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
