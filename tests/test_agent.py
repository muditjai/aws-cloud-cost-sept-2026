from __future__ import annotations

import asyncio
import copy
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aws_cloud_cost_agent.agent import (
    RESPAN_BASE_URL,
    _respan_client,
    run_markdown_agent,
)
from aws_cloud_cost_agent.tools.function_tool import tool


class _FakeMessage:
    def __init__(self, content: str | None, tool_calls: list[SimpleNamespace]) -> None:
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none: bool = True) -> dict[str, object]:
        del exclude_none
        result: dict[str, object] = {"role": "assistant"}
        if self.content is not None:
            result["content"] = self.content
        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": item.id,
                    "type": "function",
                    "function": {
                        "name": item.function.name,
                        "arguments": item.function.arguments,
                    },
                }
                for item in self.tool_calls
            ]
        return result


class _FakeCompletions:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []
        call = SimpleNamespace(
            id="call-1",
            function=SimpleNamespace(name="echo", arguments='{"value":"billing"}'),
        )
        self.messages = [_FakeMessage(None, [call]), _FakeMessage("# Complete", [])]

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.requests.append(copy.deepcopy(kwargs))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=self.messages[len(self.requests) - 1])]
        )


class AgentTests(unittest.TestCase):
    def test_agent_executes_local_tool_and_returns_markdown(self) -> None:
        @tool
        def echo(value: str) -> str:
            """Echo a value."""
            return value.upper()

        completions = _FakeCompletions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        with patch("aws_cloud_cost_agent.agent._respan_client", return_value=client):
            result = asyncio.run(
                run_markdown_agent("Test", "Analyze", [echo], model="test/model")
            )

        self.assertEqual(result, "# Complete")
        self.assertEqual(completions.requests[0]["model"], "test/model")
        second_messages = completions.requests[1]["messages"]
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertEqual(second_messages[-1]["content"], "BILLING")

    def test_agent_requires_respan_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "RESPAN_API_KEY"):
                asyncio.run(run_markdown_agent("Test", "Analyze", []))

    def test_respan_client_uses_fixed_gateway(self) -> None:
        with patch.dict(os.environ, {"RESPAN_API_KEY": "test-key"}, clear=True):
            with patch("aws_cloud_cost_agent.agent.OpenAI") as client_class:
                _respan_client()

        client_class.assert_called_once_with(
            base_url=RESPAN_BASE_URL,
            api_key="test-key",
        )


if __name__ == "__main__":
    unittest.main()
