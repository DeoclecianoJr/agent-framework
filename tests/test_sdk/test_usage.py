import pytest
from ai_framework.core.llm import calculate_cost, get_llm

def test_calculate_cost():
    tokens = {"prompt_tokens": 1000, "completion_tokens": 1000}
    
    # OpenAI GPT-4
    cost = calculate_cost(tokens, "openai", "gpt-4")
    assert cost == 0.03 + 0.06
    
    # Anthropic Claude-3-Haiku
    cost = calculate_cost(tokens, "anthropic", "claude-3-haiku")
    assert cost == 0.00025 + 0.00125

def test_calculate_cost_unknown():
    tokens = {"prompt_tokens": 1000, "completion_tokens": 1000}
    cost = calculate_cost(tokens, "invalid", "model")
    assert cost == 0.0

@pytest.mark.asyncio
async def test_mock_llm_usage_tracking():
    llm = get_llm("mock")
    response = await llm.chat([{"role": "user", "content": "hello world"}])
    
    assert "usage" in response
    assert response["usage"]["prompt_tokens"] == 2 # "hello world"
    assert response["usage"]["completion_tokens"] == 1 # "mock-response" is 1 word in count_tokens
    assert response["usage"]["total_tokens"] == 3
    assert response["usage"]["cost"] == 0.0
