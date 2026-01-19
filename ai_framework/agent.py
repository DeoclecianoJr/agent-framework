"""Agent registry and definition helpers for the SDK.

Provides a lightweight registry so agents can be declared with decorators
and retrieved later by name.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class AgentDefinition:
    """Metadata and handler reference for a registered agent."""

    name: str
    handler: Callable[..., Any]
    description: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


class Agent:
    """High-level Agent class for easier interaction."""

    def __init__(
        self,
        name: str,
        model: str = "mock",
        description: Optional[str] = None,
        memory_strategy: str = "buffer",
        tools: Optional[list] = None
    ) -> None:
        self.name = name
        self.model = model
        self.description = description
        self.memory_strategy = memory_strategy
        self.tools = tools or []


class AgentRegistry:

    """Singleton registry for agent definitions."""

    _instance: Optional["AgentRegistry"] = None

    def __init__(self) -> None:
        self._agents: Dict[str, AgentDefinition] = {}

    @classmethod
    def instance(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, definition: AgentDefinition) -> AgentDefinition:
        """Register or overwrite an agent definition."""
        self._agents[definition.name] = definition
        return definition

    def get(self, name: str) -> AgentDefinition:
        """Retrieve an agent definition by name."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' is not registered")
        return self._agents[name]

    def all(self) -> Dict[str, AgentDefinition]:
        """Return a copy of all registered agents."""
        return dict(self._agents)


def register_agent(definition: AgentDefinition) -> AgentDefinition:
    """Convenience wrapper to register an agent definition."""
    return AgentRegistry.instance().register(definition)


def get_agent(name: str) -> AgentDefinition:
    """Convenience wrapper to fetch an agent by name."""
    return AgentRegistry.instance().get(name)
