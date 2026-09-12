from __future__ import annotations

from typing import Any

from agents import Agent, Runner, WebSearchTool


async def run_markdown_agent(
    name: str,
    prompt: str,
    tools: list[Any],
    use_web_search: bool = False,
) -> str:
    """Run one focused agent and return its Markdown output."""
    agent_tools = list(tools)

    if use_web_search:
        agent_tools.append(WebSearchTool(search_context_size="medium"))

    agent = Agent(
        name=name,
        instructions="Return only the requested Markdown assessment. Never expose credentials or secrets.",
        tools=agent_tools,
    )
    result = await Runner.run(agent, prompt)
    return str(result.final_output or "")
