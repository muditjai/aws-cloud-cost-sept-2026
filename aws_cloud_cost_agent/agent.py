from __future__ import annotations

from agents import Agent, WebSearchTool

from .tools.tools_main import AwsToolConfig, create_aws_tools


BASE_INSTRUCTIONS = """
You are an AWS cloud cost optimization agent for Migracle.

Your job is to inspect AWS billing data, identify realistic cost-reduction opportunities, spawn specialist analysis for the largest services/SKUs, and produce Markdown assessment artifacts.

Required workflow:
1. Read tools/tools.md first with read_tools_registry and only use the implemented tools listed there.
2. Identify the AWS account with get_account_identity.
3. Make exploratory AWS Billing and Cost Explorer API calls through the available tools.
4. Use get_top_cost_drivers to identify the largest account-level cost drivers.
5. For each top service/SKU driver requested by the run prompt, spawn the service specialist sub-agent with analyze_service_cost_driver.
6. For missing AWS data or missing action capability, use web search to research the relevant AWS API and then call record_proposed_tool so tools/proposed_tools.md captures the missing tool.
7. Write account-level and service-level Markdown reports into the assessment folder with write_assessment_file.
8. For every optimization action you are considering, call stage_change_plan so optmization_script/considered_actions.py contains the proposed code-level action list.
9. Do not claim that an AWS resource was changed unless a mutating tool explicitly reports success.

Final output format:
- Scope
- Assessment files written
- Cost drivers
- Service/SKU specialist findings
- Proposed tools added
- Optimization action file
- Human approval required before changes
- Unknowns and data gaps

For each opportunity, include expected savings direction, confidence, operational risk, validation steps, rollback strategy, and whether it requires human approval.
"""


SERVICE_SPECIALIST_INSTRUCTIONS = """
You are an AWS service/SKU cost specialist.

Analyze one service or service/SKU cost driver deeply. Use the AWS cost tools to inspect usage type, operation, region, and other available Cost Explorer dimensions. Use web search only when AWS API coverage or optimization mechanics are unclear.

Return Markdown with:
- Service or SKU scope
- Cost facts from AWS Billing APIs
- Main usage drivers
- Likely waste patterns
- Optimization ideas
- Additional AWS tools needed, if any
- Validation and rollback notes

Do not stage changes directly. The parent agent owns assessment files and optimization action files.
"""


def create_cost_agent(config: AwsToolConfig, model: str | None = None) -> Agent:
    """Create the AWS cost analysis agent."""
    specialist_kwargs = {
        "name": "AWS Service SKU Cost Specialist",
        "handoff_description": "Specialist for deep cost analysis of one AWS service or SKU driver.",
        "instructions": SERVICE_SPECIALIST_INSTRUCTIONS,
        "tools": [
            *create_aws_tools(config, include_artifact_tools=False),
            WebSearchTool(search_context_size="medium"),
        ],
    }

    if model:
        specialist_kwargs["model"] = model

    specialist_agent = Agent(**specialist_kwargs)
    kwargs = {
        "name": "AWS Cloud Cost Agent September 2026",
        "instructions": BASE_INSTRUCTIONS,
        "tools": [
            *create_aws_tools(config),
            specialist_agent.as_tool(
                tool_name="analyze_service_cost_driver",
                tool_description="Spawn a specialist sub-agent to analyze one top AWS service or SKU cost driver.",
            ),
            WebSearchTool(search_context_size="medium"),
        ],
    }

    if model:
        kwargs["model"] = model

    return Agent(**kwargs)
