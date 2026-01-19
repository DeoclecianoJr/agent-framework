"""Memory strategies for managing conversation context.

Provides different ways to store, retrieve, and prune message history.
"""
import abc
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage


class BaseMemory(abc.ABC):
    """Abstract base class for memory strategies."""

    @abc.abstractmethod
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the memory."""
        pass

    @abc.abstractmethod
    def get_messages(self) -> List[Dict[str, str]]:
        """Retrieve stored messages in a format compatible with LLM calls."""
        pass

    @abc.abstractmethod
    def clear(self) -> None:
        """Clear all stored messages."""
        pass


class BufferMemory(BaseMemory):
    """Stores full conversation history without pruning."""

    def __init__(self) -> None:
        self.messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages.copy()

    def clear(self) -> None:
        self.messages = []


class WindowMemory(BaseMemory):
    """keeps only the last K messages (sliding window)."""

    def __init__(self, k: int = 5) -> None:
        self.k = k
        self.messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        # Keep only last 2*K messages (K turns usually means K user + K assistant)
        # But K in LangChain window memory usually refers to 'k' turns.
        # We will keep literal last 2*k messages.
        if len(self.messages) > self._get_limit():
            self.messages = self.messages[-self._get_limit():]

    def _get_limit(self) -> int:
        return self.k * 2

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages.copy()

    def clear(self) -> None:
        self.messages = []


class MemoryManager:
    """Factory and manager for memory instances."""
    
    @staticmethod
    def create(strategy: str = "buffer", **kwargs: Any) -> BaseMemory:
        """Create a memory instance based on strategy name."""
        if strategy == "buffer":
            return BufferMemory()
        elif strategy == "window":
            return WindowMemory(k=kwargs.get("k", 5))
        else:
            raise ValueError(f"Unknown memory strategy: {strategy}")
