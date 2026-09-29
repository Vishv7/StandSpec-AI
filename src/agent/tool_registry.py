"""
StandSpec AI — Tool Registry and Base Tool Interface (Phase P1-F)
Provides a provider-neutral tool registration and dispatch interface for the LLM agent.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Callable, List, Optional
import logging

logger = logging.getLogger("StandSpecToolRegistry")


@dataclass
class Tool:
    """Definition and execution contract for an individual BIS agent tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the tool handler with standardized error encapsulation."""
        try:
            res = self.handler(arguments)
            if not isinstance(res, dict):
                return {"status": "SUCCESS", "data": res}
            if "status" not in res:
                res["status"] = "SUCCESS"
            return res
        except Exception as e:
            logger.error(f"Error executing tool {self.name}: {str(e)}", exc_info=True)
            return {
                "status": "ERROR",
                "error_message": str(e),
                "tool": self.name,
            }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes tool signature for LLM context / function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }


class ToolRegistry:
    """Registry managing available BIS agent tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Registers a tool in the registry."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Retrieves a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns metadata for all registered tools."""
        return [tool.to_dict() for tool in self._tools.values()]

    def list_names(self) -> List[str]:
        """Returns list of registered tool names."""
        return list(self._tools.keys())

    def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an execution call to the specified tool."""
        tool = self.get(tool_name)
        if not tool:
            return {
                "status": "ERROR",
                "error_message": f"Unknown tool '{tool_name}'. Available tools: {', '.join(self.list_names())}",
                "tool": tool_name,
            }
        return tool.execute(arguments or {})
