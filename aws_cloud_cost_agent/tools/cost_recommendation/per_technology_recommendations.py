from __future__ import annotations

from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import (
    AwsToolConfig,
    client_error_message,
    collect_pages,
    create_boto3_session,
    json_dumps,
)


def create_cost_recommendation_tools(config: AwsToolConfig) -> list[Any]:
    """Create read-only AWS-native recommendation tools."""
    cost_explorer = create_boto3_session(config).client("ce", region_name="us-east-1")

    @tool
    def get_ec2_rightsizing_recommendations() -> str:
        """Read AWS Cost Explorer EC2 rightsizing recommendations."""
        try:
            return json_dumps(
                collect_pages(
                    cost_explorer,
                    "get_rightsizing_recommendation",
                    "RightsizingRecommendations",
                    Service="AmazonEC2",
                    Configuration={
                        "BenefitsConsidered": True,
                        "RecommendationTarget": "CROSS_INSTANCE_FAMILY",
                    },
                    PageSize=20,
                )
            )
        except (BotoCoreError, ClientError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_savings_plan_recommendations() -> str:
        """Read one-year, no-upfront Compute Savings Plan recommendations."""
        try:
            return json_dumps(
                cost_explorer.get_savings_plans_purchase_recommendation(
                    LookbackPeriodInDays="THIRTY_DAYS",
                    PaymentOption="NO_UPFRONT",
                    SavingsPlansType="COMPUTE_SP",
                    TermInYears="ONE_YEAR",
                    AccountScope="PAYER",
                )
            )
        except (BotoCoreError, ClientError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [get_ec2_rightsizing_recommendations, get_savings_plan_recommendations]
