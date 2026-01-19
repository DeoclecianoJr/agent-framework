import pytest
from unittest.mock import MagicMock, AsyncMock
from ai_framework.core.executor import AgentExecutor
from ai_framework.core.tools import ToolRegistry, tool
from ai_framework.llm import get_llm

@pytest.mark.asyncio
async def test_executor_tool_loop():
    # Setup registry with our tool
    ToolRegistry.instance()._tools = {}
    @tool(name="magic_calc")
    def magic_calc(n: int) -> int:
        """Double n."""
        return n * 2

    # Mock LLM to simulate tool calling
    llm = get_llm("mock")
    
    class ToolMockResponse:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []
    
    # First response: call tool
    resp1 = {"content": "", "raw": ToolMockResponse("", tool_calls=[{"name": "magic_calc", "args": {"n": 10}}])}
    # Second response: final answer
    resp2 = {"content": "The result is 20", "raw": ToolMockResponse("The result is 20")}
    
    llm.chat = AsyncMock(side_effect=[resp1, resp2])
    
    executor = AgentExecutor(llm)
    result = await executor.execute("session-id", "call magic_calc for 10", use_tools=True)
    
    assert result["content"] == "The result is 20"
    # Check if tool was called
    assert llm.chat.call_count == 2
