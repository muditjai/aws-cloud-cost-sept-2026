from __future__ import annotations

from typing import Any

from .auth.aws_auth import create_auth_tools
from .bill_read.aws_billing import create_billing_read_tools
from .cost_analysis.cloudfront import CLOUDFRONT_SERVICE, create_cloudfront_analysis_tools
from .cost_analysis.elb import ELB_SERVICE, create_elb_analysis_tools
from .cost_analysis.per_technology import create_cost_analysis_tools
from .cost_analysis.rds import RDS_SERVICE, create_rds_analysis_tools
from .cost_recommendation.per_technology_recommendations import create_cost_recommendation_tools
from .shared import AwsToolConfig
from .tool_management import create_tool_management_tools


def connection_tools(config: AwsToolConfig) -> list[Any]:
    return [*create_tool_management_tools(config), *create_auth_tools(config)]


def overall_bill_tools(config: AwsToolConfig) -> list[Any]:
    return [*create_tool_management_tools(config), *create_auth_tools(config), *create_billing_read_tools(config)]


def service_analysis_tools(config: AwsToolConfig, service: str | None = None) -> list[Any]:
    tools = [
        *create_tool_management_tools(config),
        *create_cost_analysis_tools(config),
    ]
    if service in {None, ELB_SERVICE}:
        tools.extend(create_elb_analysis_tools(config))
    if service in {None, RDS_SERVICE}:
        tools.extend(create_rds_analysis_tools(config))
    if service in {None, CLOUDFRONT_SERVICE}:
        tools.extend(create_cloudfront_analysis_tools(config))
    return tools


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
