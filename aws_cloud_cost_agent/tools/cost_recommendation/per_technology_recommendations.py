from __future__ import annotations

from typing import Any

from agents.decorators import tool
from botocore.exceptions import BotoCoreError, ClientError

from ..shared import (
    ACCOUNT_SCOPES,
    LOOKBACK_PERIODS,
    PAYMENT_OPTIONS,
    RI_SERVICES,
    SAVINGS_PLAN_TYPES,
    TERM_OPTIONS,
    AwsToolConfig,
    client_error_message,
    collect_pages,
    create_boto3_session,
    json_dumps,
    validate_all,
)


def create_cost_recommendation_tools(config: AwsToolConfig) -> list[Any]:
    """Create tools that read AWS-native cost recommendations."""
    session = create_boto3_session(config)
    cost_explorer = session.client("ce", region_name=config.region)

    @tool
    def get_rightsizing_recommendations(
        page_size: int = 20,
        benefits_considered: bool = True,
        recommendation_target: str = "SAME_INSTANCE_FAMILY",
    ) -> str:
        """Fetch AWS Cost Explorer EC2 rightsizing recommendations.

        Args:
            page_size: Number of recommendations to return per page.
            benefits_considered: Whether to account for RI or Savings Plans discounts.
            recommendation_target: SAME_INSTANCE_FAMILY or CROSS_INSTANCE_FAMILY.
        """
        try:
            return json_dumps(
                collect_pages(
                    cost_explorer,
                    "get_rightsizing_recommendation",
                    "RightsizingRecommendations",
                    config.max_pages,
                    Service="AmazonEC2",
                    Configuration={
                        "BenefitsConsidered": benefits_considered,
                        "RecommendationTarget": recommendation_target,
                    },
                    PageSize=page_size,
                )
            )
        except (BotoCoreError, ClientError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_savings_plans_recommendations(
        lookback_period_in_days: str = "THIRTY_DAYS",
        payment_option: str = "NO_UPFRONT",
        savings_plans_type: str = "COMPUTE_SP",
        term_in_years: str = "ONE_YEAR",
        account_scope: str = "PAYER",
    ) -> str:
        """Fetch AWS Savings Plans purchase recommendations from Cost Explorer."""
        try:
            validate_all([lookback_period_in_days], LOOKBACK_PERIODS, "lookback period")
            validate_all([payment_option], PAYMENT_OPTIONS, "payment option")
            validate_all([savings_plans_type], SAVINGS_PLAN_TYPES, "Savings Plans type")
            validate_all([term_in_years], TERM_OPTIONS, "term")
            validate_all([account_scope], ACCOUNT_SCOPES, "account scope")

            return json_dumps(
                cost_explorer.get_savings_plans_purchase_recommendation(
                    LookbackPeriodInDays=lookback_period_in_days,
                    PaymentOption=payment_option,
                    SavingsPlansType=savings_plans_type,
                    TermInYears=term_in_years,
                    AccountScope=account_scope,
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    @tool
    def get_reservation_recommendations(
        service: str = "Amazon Elastic Compute Cloud - Compute",
        lookback_period_in_days: str = "THIRTY_DAYS",
        payment_option: str = "NO_UPFRONT",
        term_in_years: str = "ONE_YEAR",
        account_scope: str = "PAYER",
    ) -> str:
        """Fetch AWS Reserved Instance purchase recommendations from Cost Explorer."""
        try:
            validate_all([service], RI_SERVICES, "reservation service")
            validate_all([lookback_period_in_days], LOOKBACK_PERIODS, "lookback period")
            validate_all([payment_option], PAYMENT_OPTIONS, "payment option")
            validate_all([term_in_years], TERM_OPTIONS, "term")
            validate_all([account_scope], ACCOUNT_SCOPES, "account scope")

            return json_dumps(
                cost_explorer.get_reservation_purchase_recommendation(
                    Service=service,
                    LookbackPeriodInDays=lookback_period_in_days,
                    PaymentOption=payment_option,
                    TermInYears=term_in_years,
                    AccountScope=account_scope,
                )
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            return json_dumps({"ok": False, "error": client_error_message(error)})

    return [
        get_rightsizing_recommendations,
        get_savings_plans_recommendations,
        get_reservation_recommendations,
    ]
