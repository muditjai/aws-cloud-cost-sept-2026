from __future__ import annotations

import json
from typing import Any

from ..function_tool import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import (
    COST_GROUP_DIMENSIONS,
    COST_METRICS,
    AwsToolConfig,
    client_error_message,
    collect_pages,
    create_boto3_session,
    csv_values,
    json_dumps,
    parse_filter,
    summarize_cost_groups,
    validate_all,
)


def fetch_cost_and_usage(
    config: AwsToolConfig,
    start_date: str,
    end_date: str,
    group_by: str,
    filter_json: str | None = None,
) -> dict[str, Any]:
    """Fetch monthly unblended costs from AWS Cost Explorer."""
    dimensions = csv_values(group_by)
    validate_all(dimensions, COST_GROUP_DIMENSIONS, "group dimensions")
    validate_all(["UnblendedCost"], COST_METRICS, "metrics")

    request: dict[str, Any] = {
        "TimePeriod": {"Start": start_date, "End": end_date},
        "Granularity": "MONTHLY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": value} for value in dimensions],
    }
    cost_filter = parse_filter(filter_json)
    if cost_filter:
        request["Filter"] = cost_filter

    client = create_boto3_session(config).client("ce", region_name="us-east-1")
    return collect_pages(client, "get_cost_and_usage", "ResultsByTime", **request)


def _money(amount: float) -> str:
    return f"-${abs(amount):,.2f}" if amount < 0 else f"${amount:,.2f}"


def _estimated(data: dict[str, Any]) -> bool:
    return any(item.get("Estimated", False) for item in data.get("items", []))


def _cost_table(rows: list[dict[str, Any]], key_headers: list[str], limit: int = 10) -> str:
    header = "| " + " | ".join([*key_headers, "Cost"]) + " |"
    separator = "|" + "|".join(["---"] * len(key_headers) + ["---:"]) + "|"
    body = []
    for row in rows[:limit]:
        keys = [str(value) for value in row.get("keys", [])]
        keys.extend(["Unknown"] * (len(key_headers) - len(keys)))
        body.append("| " + " | ".join([*keys[: len(key_headers)], _money(row["amount"])]) + " |")
    return "\n".join([header, separator, *body])


def render_overall_bill_report(
    account_id: str,
    start_date: str,
    end_date: str,
    service_data: dict[str, Any],
    region_data: dict[str, Any],
    service_sku_data: dict[str, Any],
) -> str:
    """Render Cost Explorer totals deterministically rather than asking a model to calculate them."""
    services = summarize_cost_groups(service_data, "UnblendedCost")
    regions = summarize_cost_groups(region_data, "UnblendedCost")
    service_skus = summarize_cost_groups(service_sku_data, "UnblendedCost")
    service_total = sum(row["amount"] for row in services)
    region_total = sum(row["amount"] for row in regions)
    service_sku_total = sum(row["amount"] for row in service_skus)
    includes_estimates = any(_estimated(data) for data in (service_data, region_data, service_sku_data))

    return f"""# Overall AWS Bill

- **Account:** `{account_id}`
- **Billing period:** `{start_date}` through `{end_date}` (end date exclusive)
- **Metric:** Unblended cost
- **Total cost:** **{_money(service_total)} USD**
- **Includes estimated charges:** {"Yes" if includes_estimates else "No"}

## Top Services

{_cost_table(services, ["Service"])}

## Top Regions

{_cost_table(regions, ["Region"])}

## Top Service/Usage-Type Pairs

{_cost_table(service_skus, ["Service", "Usage type"])}

## Validation

| Grouping | Calculated total |
|---|---:|
| Service | {_money(service_total)} |
| Region | {_money(region_total)} |
| Service / usage type | {_money(service_sku_total)} |

## Data Limitations

- Cost Explorer may mark recent charges as estimated; those values can change before invoicing.
- Unblended costs may differ from amortized costs, credits, refunds, taxes, and the final invoice.
- AWS Cost Explorer usage type is used as the SKU-level dimension.
"""


def build_overall_bill_report(
    config: AwsToolConfig,
    account_id: str,
    start_date: str,
    end_date: str,
) -> str:
    """Retrieve the three overall bill groupings and render one local Markdown report."""
    service_data = fetch_cost_and_usage(config, start_date, end_date, "SERVICE")
    region_data = fetch_cost_and_usage(config, start_date, end_date, "REGION")
    service_sku_data = fetch_cost_and_usage(config, start_date, end_date, "SERVICE,USAGE_TYPE")
    return render_overall_bill_report(
        account_id,
        start_date,
        end_date,
        service_data,
        region_data,
        service_sku_data,
    )


def create_billing_read_tools(config: AwsToolConfig) -> list[Any]:
    """Create the overall billing data tool."""

    @tool
    def get_bill_data(start_date: str, end_date: str, group_by: str = "SERVICE") -> str:
        """Read monthly AWS costs grouped by SERVICE, REGION, USAGE_TYPE, or OPERATION."""
        try:
            return json_dumps(fetch_cost_and_usage(config, start_date, end_date, group_by))
        except (BotoCoreError, ClientError, ValueError, json.JSONDecodeError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [get_bill_data]
