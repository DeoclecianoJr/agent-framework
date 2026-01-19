"""Compatibility wrapper for LLM access."""
from ai_framework.core.llm import BaseLLM, MockLLM, count_tokens, get_llm, LLMProvider

__all__ = ["BaseLLM", "MockLLM", "count_tokens", "get_llm", "LLMProvider"]
