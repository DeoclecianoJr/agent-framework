"""Utility functions for LLM operations."""
from typing import Optional, Dict


def count_tokens(text: Optional[str]) -> int:
    """Naive token counter placeholder (word-based).
    
    In the future, this should use tiktoken or provider-specific counters.
    
    Args:
        text: Input text to count tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return max(len(text.split()), 1)


def calculate_cost(tokens: Dict[str, int], provider: str, model: str) -> float:
    """Calculate approximate cost based on tokens and provider.
    
    Args:
        tokens: Dict with 'prompt_tokens' and 'completion_tokens'
        provider: LLM provider name
        model: Model name
        
    Returns:
        Estimated cost in USD
    """
    # Prices per 1k tokens (example prices)
    prices = {
        "openai": {
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        },
        "anthropic": {
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
        }
    }
    
    if provider not in prices or model not in prices[provider]:
        return 0.0
        
    p = prices[provider][model]
    prompt_cost = (tokens.get("prompt_tokens", 0) / 1000) * p["prompt"]
    completion_cost = (tokens.get("completion_tokens", 0) / 1000) * p["completion"]
    
    return round(prompt_cost + completion_cost, 6)
