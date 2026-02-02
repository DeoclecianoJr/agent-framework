"""Guardrails and safety mechanisms for content moderation.

Provides topic blocklists, confidence thresholds, and fallback behavior.
"""
import re
from typing import List, Optional, Set, Dict, Any


class GuardrailViolation(Exception):
    """Raised when a guardrail policy is violated."""
    
    def __init__(self, message: str, topic: Optional[str] = None, is_theme_violation: bool = False):
        self.message = message
        self.topic = topic
        self.is_theme_violation = is_theme_violation
        super().__init__(self.message)


class GuardrailProcessor:
    """Processes content against safety and topic policies."""

    NEUTRAL_KEYWORDS = {
        "olá", "oi", "oie", "bom dia", "boa tarde", "boa noite", 
        "hello", "hi", "hey", "tudo bem", "como vai",
        "obrigado", "obrigada", "thanks", "thank you",
        "tchau", "bye", "adeus", "ajuda", "valeu", "vlw",
        "ok", "entendi", "compreendi", "pode ser", "beleza"
    }

    def __init__(
        self, 
        llm: Optional[Any] = None,
        blocklist: Optional[List[str]] = None,
        allowlist: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        allowed_themes: Optional[List[str]] = None,
        tool_restrictions: Optional[Dict[str, List[str]]] = None
    ):
        self.llm = llm
        self.blocklist = [b.lower() for b in (blocklist or [])]
        self.allowlist = [a.lower() for a in (allowlist or [])]
        self.min_confidence = min_confidence
        self.allowed_themes = [t.lower() for t in (allowed_themes or [])]
        # tool_restrictions format: {"agent_id": ["allowed_tool1", "allowed_tool2"]}
        # or {"*": ["globally_allowed_tool1"]} for global restrictions
        self.tool_restrictions = tool_restrictions or {}

    def validate_input(self, text: str) -> None:
        """Validate user input against policies.
        
        Args:
            text: User input text
            
        Raises:
            GuardrailViolation: If input violates a policy
        """
        # Validação de entrada removida conforme solicitado
        pass

    def validate_output(self, content: str, confidence: float = 1.0) -> str:
        """Validate agent output against policies.
        
        Args:
            content: Generated response content
            confidence: LLM confidence score
            
        Returns:
            Validated content or fallback message
        """
        if confidence < self.min_confidence:
            return "Sinto muito, mas não tenho certeza suficiente para responder a essa pergunta com precisão."
            
        return content
    
    def validate_tool_usage(self, agent_id: str, tool_name: str) -> bool:
        """Validate if an agent is allowed to use a specific tool.
        
        Args:
            agent_id: ID of the agent requesting tool usage
            tool_name: Name of the tool being requested
            
        Returns:
            True if tool usage is allowed, False otherwise
        """
        # If no tool restrictions configured, allow all tools
        if not self.tool_restrictions:
            return True
        
        # Check agent-specific restrictions first
        if agent_id in self.tool_restrictions:
            allowed_tools = self.tool_restrictions[agent_id]
            return tool_name in allowed_tools
        
        # Check global restrictions (wildcard "*")
        if "*" in self.tool_restrictions:
            allowed_tools = self.tool_restrictions["*"]
            return tool_name in allowed_tools
        
        # If agent not in restrictions but restrictions exist, default to allow
        # (this allows opt-in restrictions per agent)
        return True
    
    def get_allowed_tools(self, agent_id: str) -> Optional[List[str]]:
        """Get list of allowed tools for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of allowed tools, or None if no restrictions
        """
        if agent_id in self.tool_restrictions:
            return self.tool_restrictions[agent_id].copy()
        
        if "*" in self.tool_restrictions:
            return self.tool_restrictions["*"].copy()
            
        return None

    @classmethod
    def from_config(cls, config: Dict[str, Any], llm: Optional[Any] = None) -> "GuardrailProcessor":
        """Create processor from agent configuration dictionary.
        
        Expected config structure:
        {
            "guardrails": {
                "blocklist": ["topic1", "topic2"],
                "allowlist": ["topic3"],
                "allowed_themes": ["framework", "ai"],
                "min_confidence": 0.7,
                "tool_restrictions": {
                    "agent_id": ["tool1", "tool2"],
                    "*": ["global_tool"]
                }
            }
        }
        """
        g_config = config.get("guardrails", {})
        return cls(
            llm=llm,
            blocklist=g_config.get("blocklist"),
            allowlist=g_config.get("allowlist"),
            min_confidence=g_config.get("min_confidence", 0.0),
            allowed_themes=g_config.get("allowed_themes"),
            tool_restrictions=g_config.get("tool_restrictions", {})
        )
