from __future__ import annotations

from typing import Any

from .auth.aws_auth import create_auth_tools
from .bill_read.aws_billing import create_billing_read_tools
from .cost_analysis.per_technology import create_cost_analysis_tools
from .cost_recommendation.per_technology_recommendations import create_cost_recommendation_tools
from .shared import AwsToolConfig
from .tool_management import create_tool_management_tools


def connection_tools(config: AwsToolConfig) -> list[Any]:
    return [*create_tool_management_tools(config), *create_auth_tools(config)]


def overall_bill_tools(config: AwsToolConfig) -> list[Any]:
    return [*create_tool_management_tools(config), *create_auth_tools(config), *create_billing_read_tools(config)]


def service_analysis_tools(config: AwsToolConfig) -> list[Any]:
    return [*create_tool_management_tools(config), *create_cost_analysis_tools(config)]


def recommendation_tools(config: AwsToolConfig) -> list[Any]:
    return [
        *create_tool_management_tools(config),
        *create_cost_analysis_tools(config),
        *create_cost_recommendation_tools(config),
    ]


__all__ = [
    "AwsToolConfig",
    "connection_tools",
    "overall_bill_tools",
    "recommendation_tools",
    "service_analysis_tools",
]
