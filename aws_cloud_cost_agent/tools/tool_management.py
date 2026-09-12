from __future__ import annotations

from typing import Any

from .function_tool import tool
from .shared import AwsToolConfig, json_dumps


def create_tool_management_tools(config: AwsToolConfig) -> list[Any]:
    """Create tools for reading the registry and recording missing capabilities."""

    @tool
    def read_tools_registry() -> str:
        """Read the implemented tool registry."""
        return (config.tools_dir / "tools.md").read_text(encoding="utf-8")

    @tool
    def propose_missing_tool(name: str, reason: str, aws_apis: list[str]) -> str:
        """Append a missing tool request to proposed_tools.md."""
        path = config.tools_dir / "proposed_tools.md"
        with path.open("a", encoding="utf-8") as file:
            file.write(
                f"\n## {name}\n\n"
                f"- Reason: {reason}\n"
                f"- AWS APIs: {', '.join(aws_apis)}\n"
            )
        return json_dumps({"ok": True, "path": str(path)})

    return [read_tools_registry, propose_missing_tool]
