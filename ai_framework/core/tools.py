"""Tool registry and definition system.

Allows functions to be decorated as tools and automatically converted
to LangChain-compatible tool definitions.
"""
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model


@dataclass
class ToolDefinition:
    """Metadata for a registered tool."""
    name: str
    func: Callable[..., Any]
    description: str
    args_schema: Optional[Type[BaseModel]] = None


class ToolRegistry:
    """Registry for managing available tools."""
    
    _instance: Optional["ToolRegistry"] = None
    
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: ToolDefinition) -> ToolDefinition:
        """Register a new tool."""
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> ToolDefinition:
        """Retrieve a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]

    def all(self) -> List[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())

    def to_langchain(self) -> List[StructuredTool]:
        """Convert all registered tools to LangChain StructuredTools."""
        return [
            StructuredTool.from_function(
                func=t.func,
                name=t.name,
                description=t.description,
                args_schema=t.args_schema
            )
            for t in self._tools.values()
        ]


def tool(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to register a function as a tool.
    
    Args:
        name: Override function name as tool name.
        description: Override function docstring as tool description.
    """
    def decorator(func: Callable[..., Any]):
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"Tool for {tool_name}"
        
        # Identify args schema from type hints
        # For MVP, we use LangChain's auto-inference but we could also manually build it.
        
        definition = ToolDefinition(
            name=tool_name,
            func=func,
            description=tool_desc
        )
        ToolRegistry.instance().register(definition)
        return func
        
    return decorator
