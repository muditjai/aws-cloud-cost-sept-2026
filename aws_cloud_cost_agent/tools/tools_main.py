from __future__ import annotations

from typing import Any

from .artifacts.assessment_artifacts import create_artifact_tools, prepare_output_dirs
from .auth.aws_auth import create_auth_tools
from .bill_read.aws_billing import create_billing_read_tools
from .cost_analysis.per_technology import create_per_technology_analysis_tools
from .cost_recommendation.per_technology_recommendations import create_cost_recommendation_tools
from .shared import AwsToolConfig


def create_aws_tools(config: AwsToolConfig, include_artifact_tools: bool = True) -> list[Any]:
    """Import and assemble every implemented tool group for the agent."""
    tools: list[Any] = []

    if include_artifact_tools:
        tools.extend(create_artifact_tools(config))

    tools.extend(create_auth_tools(config))
    tools.extend(create_billing_read_tools(config))
    tools.extend(create_per_technology_analysis_tools(config))
    tools.extend(create_cost_recommendation_tools(config))

    return tools


__all__ = ["AwsToolConfig", "create_aws_tools", "prepare_output_dirs"]
