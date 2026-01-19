"""Decorators to register agents and tools with the SDK registry."""
from functools import wraps
from typing import Any, Callable, Dict, Optional

from ai_framework.agent import AgentDefinition, AgentRegistry
from ai_framework.core.tools import ToolRegistry, tool as real_tool


def agent(

    name: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register an agent.

    Args:
        name: Optional explicit agent name; defaults to function name.
        description: Human-readable description of the agent.
        config: Optional configuration metadata.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        agent_name = name or func.__name__
        definition = AgentDefinition(
            name=agent_name,
            handler=func,
            description=description,
            config=config or {},
        )
        AgentRegistry.instance().register(definition)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a tool function.

    Registers the function with the ToolRegistry for discovery and execution.
    """
    return real_tool(name=name, description=description)


def list_tools() -> Dict[str, Any]:
    """List all registered tools from the registry."""
    return {
        t.name: {
            "description": t.description,
            "handler": t.func
        }
        for t in ToolRegistry.instance().all()
    }



