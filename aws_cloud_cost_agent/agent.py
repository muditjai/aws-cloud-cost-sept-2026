from __future__ import annotations

import asyncio
import json
import os

from openai import OpenAI

from .tools.function_tool import FunctionTool


RESPAN_BASE_URL = "https://api.respan.ai/api/"
RESPAN_MODEL = "openai/gpt-6-astra"
MAX_TOOL_ROUNDS = 20


def _respan_client() -> OpenAI:
    api_key = os.getenv("RESPAN_API_KEY")
    if not api_key:
        raise RuntimeError("RESPAN_API_KEY is required for analysis and recommendations.")
    return OpenAI(
        base_url=RESPAN_BASE_URL,
        api_key=api_key,
    )


def _tool_definition(item: FunctionTool) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": item.name,
            "description": item.description,
            "parameters": item.params_json_schema,
        },
    }


async def run_markdown_agent(
    name: str,
    prompt: str,
    tools: list[FunctionTool],
    use_web_search: bool = False,
) -> str:
    """Run one focused Respan chat-completions agent with local AWS tools."""
    client = _respan_client()
    tool_map = {item.name: item for item in tools}
    system_prompt = (
        f"You are {name}. Return only the requested Markdown assessment. "
        "Never expose credentials or secrets. Use the provided tools for AWS facts."
    )
    if use_web_search:
        system_prompt += (
            " This Chat Completions gateway has no built-in web-search tool. "
            "Do not claim that current web research was performed; record a missing tool when it is required."
        )
    messages: list[dict[str, object]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    definitions = [_tool_definition(item) for item in tools]

    for _ in range(MAX_TOOL_ROUNDS):
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=RESPAN_MODEL,
            messages=messages,
            tools=definitions,
            tool_choice="auto",
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            if not message.content:
                raise RuntimeError("Respan returned an empty agent response.")
            return message.content

        for tool_call in message.tool_calls:
            selected = tool_map.get(tool_call.function.name)
            try:
                if not selected:
                    raise ValueError(f"Unknown tool: {tool_call.function.name}")
                output = await asyncio.to_thread(
                    selected.invoke_json,
                    tool_call.function.arguments,
                )
            except Exception as error:
                output = json.dumps({"ok": False, "error": str(error)})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": output,
                }
            )

    raise RuntimeError(f"Respan exceeded the {MAX_TOOL_ROUNDS}-round tool-call limit.")
