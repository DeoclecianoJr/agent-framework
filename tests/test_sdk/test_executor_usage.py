import pytest
import uuid
from unittest.mock import AsyncMock, patch
from ai_framework.core.llm import get_llm
from ai_framework.core.executor import AgentExecutor
from ai_framework.core.tools import ToolRegistry, tool

@pytest.mark.asyncio
async def test_executor_accumulates_usage():
    """Verify that multiple LLM calls in the reasoning loop accumulate usage."""
    llm = get_llm("mock")
    executor = AgentExecutor(llm=llm)
    
    # We'll use the instance for the decorator-based registration
    registry = ToolRegistry.instance()
    
    # Clear registry for clean test
    registry._tools = {}
    
    # Mocking two LLM calls
    # Call 1: Requests a tool
    # Call 2: Final response
    responses = [
        {
            "content": "I need to use a tool.",
            "tool_calls": [{"name": "get_weather", "args": {"location": "London"}, "id": "call_1"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": 0.01}
        },
        {
            "content": "The weather is nice.",
            "tool_calls": [],
            "usage": {"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20, "cost": 0.02}
        }
    ]
    
    @tool(name="get_weather")
    async def get_weather(location: str):
        """Get weather for location."""
        return f"Nice in {location}"


    # We need to mock the underlying tool registration in the executor context or pass it
    # AgentExecutor doesn't take registry in __init__, but execute takes use_tools=True
    
    with patch.object(executor.llm, "chat", side_effect=responses):
        session_id = str(uuid.uuid4())
        response = await executor.execute(
            session_id=session_id,
            message_content="What is the weather?", 
            tool_registry=registry
        )
        
        # Total usage should be sum of both calls
        usage = response["metadata"]["usage"]
        assert usage["prompt_tokens"] == 25
        assert usage["completion_tokens"] == 10
        assert usage["total_tokens"] == 35
        assert usage["cost"] == pytest.approx(0.03)
        assert response["content"] == "The weather is nice."

