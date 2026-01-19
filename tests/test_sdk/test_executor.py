"""Tests for AgentExecutor (Task 2.4)."""
import pytest
from ai_framework.llm import MockLLM
from ai_framework.core.executor import AgentExecutor


@pytest.mark.asyncio
async def test_executor_formats_messages_correctly():
    """Verify executor includes history and new message in correct order."""
    class CaptureLLM(MockLLM):
        def __init__(self):
            super().__init__()
            self.captured_messages = None
        async def chat(self, messages, **kwargs):
            self.captured_messages = messages
            return await super().chat(messages, **kwargs)

    mock_llm = CaptureLLM()
    executor = AgentExecutor(llm=mock_llm)
    
    history = [
        {"role": "user", "content": "Prev user"},
        {"role": "assistant", "content": "Prev assistant"}
    ]
    message = "Current message"
    
    await executor.execute("session-123", message, history=history)
    
    assert len(mock_llm.captured_messages) == 3
    assert mock_llm.captured_messages[0]["content"] == "Prev user"
    assert mock_llm.captured_messages[1]["content"] == "Prev assistant"
    assert mock_llm.captured_messages[2]["content"] == "Current message"


@pytest.mark.asyncio
async def test_executor_calculates_tokens():
    """Verify basic token counting is included in result metadata."""
    mock_llm = MockLLM(response_text="Hello world")
    executor = AgentExecutor(llm=mock_llm)
    
    # "New message" = 2 words
    # "Hello world" = 2 words
    result = await executor.execute("session-id", "New message")
    
    assert result["content"] == "Hello world"
    # usage: {'prompt_tokens': 2, 'completion_tokens': 2, 'total_tokens': 4, 'cost': 0.0}
    usage = result["metadata"]["usage"]
    assert usage["prompt_tokens"] == 2
    assert usage["completion_tokens"] == 2
    assert usage["total_tokens"] == 4

