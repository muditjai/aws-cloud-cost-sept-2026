from __future__ import annotations

import unittest

from aws_cloud_cost_agent.tools.function_tool import tool


class FunctionToolTests(unittest.TestCase):
    def test_schema_and_invocation(self) -> None:
        @tool
        def sample(name: str, aws_apis: list[str], region: str = "us-east-1") -> str:
            """Build a sample result."""
            return f"{name}:{region}:{','.join(aws_apis)}"

        self.assertEqual(sample.name, "sample")
        self.assertEqual(sample.description, "Build a sample result.")
        self.assertEqual(sample.params_json_schema["required"], ["name", "aws_apis"])
        self.assertEqual(
            sample.params_json_schema["properties"]["aws_apis"],
            {"type": "array", "items": {"type": "string"}},
        )
        self.assertEqual(
            sample.invoke_json('{"name":"tool","aws_apis":["ce:GetCostAndUsage"]}'),
            "tool:us-east-1:ce:GetCostAndUsage",
        )


if __name__ == "__main__":
    unittest.main()
