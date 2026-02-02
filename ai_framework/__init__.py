"""AI Framework SDK public API - Simplified for production testing."""

# Simplified imports
from ai_framework.llm import BaseLLM, MockLLM, get_llm, count_tokens

# Simplified decorators for production testing
def agent(name: str = None, **kwargs):
    """Simplified agent decorator for production testing"""
    def decorator(func):
        func._is_agent = True
        func._agent_name = name or func.__name__
        func._agent_config = kwargs
        return func
    return decorator

def tool(name: str = None, description: str = None, **kwargs):
    """Simplified tool decorator for production testing"""
    def decorator(func):
        func._is_tool = True
        func._tool_name = name or func.__name__
        func._tool_description = description or func.__doc__
        func._tool_config = kwargs
        return func
    return decorator

__version__ = "0.1.0-prod"

__all__ = [
    "agent",
    "tool",
    "BaseLLM",
    "MockLLM",
    "get_llm",
    "count_tokens",
]
