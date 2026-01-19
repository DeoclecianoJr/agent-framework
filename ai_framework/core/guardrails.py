"""Guardrails and safety mechanisms for content moderation.

Provides topic blocklists, confidence thresholds, and fallback behavior.
"""
import re
from typing import List, Optional, Set, Dict, Any


class GuardrailViolation(Exception):
    """Raised when a guardrail policy is violated."""
    
    def __init__(self, message: str, topic: Optional[str] = None):
        self.message = message
        self.topic = topic
        super().__init__(self.message)


class GuardrailProcessor:
    """Processes content against safety and topic policies."""

    def __init__(
        self, 
        blocklist: Optional[List[str]] = None,
        allowlist: Optional[List[str]] = None,
        min_confidence: float = 0.0
    ):
        self.blocklist = [b.lower() for b in (blocklist or [])]
        self.allowlist = [a.lower() for a in (allowlist or [])]
        self.min_confidence = min_confidence

    def validate_input(self, text: str) -> None:
        """Validate user input against policies.
        
        Args:
            text: User input text
            
        Raises:
            GuardrailViolation: If input violates a policy
        """
        text_lower = text.lower()
        
        # 1. Check blocklist (keyword based for MVP)
        for blocked in self.blocklist:
            if re.search(rf"\b{re.escape(blocked)}\b", text_lower):
                raise GuardrailViolation(
                    f"Message contains blocked topic: {blocked}",
                    topic=blocked
                )
                
        # 2. Check allowlist if present
        if self.allowlist:
            found = False
            for allowed in self.allowlist:
                if re.search(rf"\b{re.escape(allowed)}\b", text_lower):
                    found = True
                    break
            if not found:
                raise GuardrailViolation("Message does not contain any allowed topics")

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

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "GuardrailProcessor":
        """Create processor from agent configuration dictionary.
        
        Expected config structure:
        {
            "guardrails": {
                "blocklist": ["topic1", "topic2"],
                "allowlist": ["topic3"],
                "min_confidence": 0.7
            }
        }
        """
        g_config = config.get("guardrails", {})
        return cls(
            blocklist=g_config.get("blocklist"),
            allowlist=g_config.get("allowlist"),
            min_confidence=g_config.get("min_confidence", 0.0)
        )
