from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from types import UnionType
from typing import Any, Callable, Union, get_args, get_origin, get_type_hints


def _json_schema(annotation: Any) -> dict[str, Any]:
    origin = get_origin(annotation)
    if origin is list:
        arguments = get_args(annotation)
        return {
            "type": "array",
            "items": _json_schema(arguments[0] if arguments else Any),
        }
    if origin in {Union, UnionType}:
        variants = [
            _json_schema(item)
            for item in get_args(annotation)
            if item is not type(None)
        ]
        return variants[0] if len(variants) == 1 else {"anyOf": variants}
    return {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
    }.get(annotation, {})


@dataclass(frozen=True)
class FunctionTool:
    """A local function exposed through an OpenAI-compatible tool schema."""

    name: str
    description: str
    params_json_schema: dict[str, Any]
    function: Callable[..., Any]

    def invoke_json(self, arguments: str) -> str:
        values = json.loads(arguments or "{}")
        if not isinstance(values, dict):
            raise ValueError("Tool arguments must decode to a JSON object.")
        result = self.function(**values)
        return result if isinstance(result, str) else json.dumps(result, default=str)


def tool(function: Callable[..., Any]) -> FunctionTool:
    """Decorate a synchronous Python function as a chat-completions tool."""
    signature = inspect.signature(function)
    type_hints = get_type_hints(function)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, parameter in signature.parameters.items():
        properties[name] = _json_schema(type_hints.get(name, Any))
        if parameter.default is inspect.Parameter.empty:
            required.append(name)

    return FunctionTool(
        name=function.__name__,
        description=inspect.getdoc(function) or function.__name__,
        params_json_schema={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        function=function,
    )
