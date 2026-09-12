from __future__ import annotations

import json
from typing import Any

from ..function_tool import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..bill_read.aws_billing import fetch_cost_and_usage
from ..shared import (
    AwsToolConfig,
    client_error_message,
    json_dumps,
    service_filter,
    summarize_cost_groups,
)


TOP_SERVICE_SKU_COUNT = 5


def discover_top_service_skus(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Return the highest-cost service and usage-type pairs for orchestration."""
    costs = fetch_cost_and_usage(config, start_date, end_date, "SERVICE,USAGE_TYPE")
    drivers = summarize_cost_groups(costs, "UnblendedCost")
    return [driver for driver in drivers if driver["amount"] > 0][:TOP_SERVICE_SKU_COUNT]


def create_cost_analysis_tools(config: AwsToolConfig) -> list[Any]:
    """Create tools for in-depth analysis of one service or SKU."""

    @tool
    def get_top_service_skus(start_date: str, end_date: str) -> str:
        """Return the five highest-cost AWS service and usage-type pairs."""
        try:
            return json_dumps(discover_top_service_skus(config, start_date, end_date))
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_service_sku_breakdown(service: str, start_date: str, end_date: str) -> str:
        """Break one AWS service down by usage type, operation, and region."""
        try:
            filter_json = json.dumps(service_filter(service))
            result = {
                "service": service,
                "by_usage_and_operation": fetch_cost_and_usage(
                    config, start_date, end_date, "USAGE_TYPE,OPERATION", filter_json
                ),
                "by_region": fetch_cost_and_usage(
                    config, start_date, end_date, "REGION", filter_json
                ),
            }
            return json_dumps(result)
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [get_top_service_skus, get_service_sku_breakdown]
