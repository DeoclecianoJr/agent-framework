"""Memory strategies for managing conversation context.

Provides different ways to store, retrieve, and prune message history.
"""
import abc
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage


class BaseMemory(abc.ABC):
    """Abstract base class for memory strategies."""

    @abc.abstractmethod
    async def add_message(self, role: str, content: str) -> None:
        """Add a message to the memory."""
        pass

    @abc.abstractmethod
    async def get_messages(self) -> List[Dict[str, str]]:
        """Retrieve stored messages in a format compatible with LLM calls."""
        pass

    @abc.abstractmethod
    async def clear(self) -> None:
        """Clear all stored messages."""
        pass


class BufferMemory(BaseMemory):
    """Stores full conversation history without pruning."""

    def __init__(self) -> None:
        self.messages: List[Dict[str, str]] = []

    async def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    async def get_messages(self) -> List[Dict[str, str]]:
        return self.messages.copy()

    async def clear(self) -> None:
        self.messages = []


class WindowMemory(BaseMemory):
    """keeps only the last K messages (sliding window)."""

    def __init__(self, k: int = 5) -> None:
        self.k = k
        self.messages: List[Dict[str, str]] = []

    async def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        # Keep only last 2*K messages (K turns usually means K user + K assistant)
        if len(self.messages) > self._get_limit():
            self.messages = self.messages[-self._get_limit():]

    def _get_limit(self) -> int:
        return self.k * 2

    async def get_messages(self) -> List[Dict[str, str]]:
        return self.messages.copy()

    async def clear(self) -> None:
        self.messages = []


class SummaryMemory(BaseMemory):
    """Summarizes older messages while keeping the most recent ones in budget."""

    def __init__(self, llm: Any, max_messages: int = 15, summary: Optional[str] = None, language: str = "português") -> None:
        """Initialize summary memory.
        
        Args:
            llm: LLM instance to use for summarization.
            max_messages: Maximum number of messages to keep before summarizing.
            summary: Initial summary text if any.
            language: Language for the summary text.
        """
        self.llm = llm
        self.max_messages = max_messages
        self.recent_messages: List[Dict[str, str]] = []
        self.summary: Optional[str] = summary
        self.language = language
        self.summary_updated = False

    async def add_message(self, role: str, content: str, summarize: bool = True) -> None:
        self.recent_messages.append({"role": role, "content": content})
        if summarize and len(self.recent_messages) >= self.max_messages:
            await self._summarize()

    async def _summarize(self) -> None:
        """Summarize all current messages and clear the buffer."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Summarizing {len(self.recent_messages)} messages. Current memory state: {len(self.recent_messages)} messages.")
        
        # Include current summary + all recent messages in the new summary
        messages_text = "\n".join([f"{m['role']}: {m['content']}" for m in self.recent_messages])
        
        prompt = [
            {"role": "system", "content": f"Você é um sumarizador de conversas. Resuma progressivamente as linhas fornecidas, adicionando-as ao resumo anterior. Seja conciso, mas mantenha os detalhes importantes. O resumo DEVE ser em {self.language}."},
            {"role": "user", "content": f"Resumo atual: {self.summary or 'Nenhum resumo ainda.'}\n\nNovos segmentos para incluir:\n{messages_text}\n\nForneça apenas o texto do resumo atualizado em {self.language}."}
        ]
        
        try:
            resp = await self.llm.chat(prompt, temperature=0.0)
            self.summary = resp["content"]
            self.recent_messages = []
            self.summary_updated = True
        except Exception:
            # Fallback: keep messages if summarization fails
            pass

    async def get_messages(self) -> List[Dict[str, str]]:
        msgs = []
        if self.summary:
            msgs.append({"role": "system", "content": f"Resumo do contexto da conversa anterior: {self.summary}"})
        msgs.extend(self.recent_messages)
        return msgs

    async def clear(self) -> None:
        self.recent_messages = []
        self.summary = None
        self.summary_updated = True


class MemoryManager:
    """Factory and manager for memory instances."""
    
    @staticmethod
    def create(strategy: str = "buffer", **kwargs: Any) -> BaseMemory:
        """Create a memory instance based on strategy name."""
        if strategy == "buffer":
            return BufferMemory()
        elif strategy == "window":
            return WindowMemory(k=kwargs.get("k", 5))
        elif strategy == "summary":
            llm = kwargs.get("llm")
            if not llm:
                raise ValueError("Summary strategy requires an 'llm' instance")
            
            from ai_framework.core.config import settings
            max_msgs = kwargs.get("max_messages") or settings.memory_max_messages
            lang = kwargs.get("language") or settings.memory_summary_language
            
            return SummaryMemory(
                llm=llm, 
                max_messages=max_msgs,
                summary=kwargs.get("summary"),
                language=lang
            )
        else:
            raise ValueError(f"Unknown memory strategy: {strategy}")
