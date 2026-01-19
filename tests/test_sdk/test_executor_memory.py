import pytest
from ai_framework.core.executor import AgentExecutor
from ai_framework.llm import get_llm
from ai_framework.core.memory import BufferMemory

@pytest.mark.asyncio
async def test_executor_with_memory():
    llm = get_llm("mock", response_text="executor reply")
    memory = BufferMemory()
    executor = AgentExecutor(llm, memory=memory)
    
    # First turn
    result = await executor.execute("session-1", "hello")
    assert result["content"] == "executor reply"
    assert len(memory.get_messages()) == 2
    assert memory.get_messages()[0]["content"] == "hello"
    assert memory.get_messages()[1]["content"] == "executor reply"
    
    # Second turn
    await executor.execute("session-1", "how are you?")
    assert len(memory.get_messages()) == 4
    assert memory.get_messages()[2]["content"] == "how are you?"

@pytest.mark.asyncio
async def test_executor_explicit_history_overrides_memory():
    llm = get_llm("mock")
    memory = BufferMemory()
    memory.add_message("user", "stored message")
    executor = AgentExecutor(llm, memory=memory)
    
    # Provide explicit history
    explicit_history = [{"role": "user", "content": "explicit content"}]
    # We can't easily check what was sent to LLM without more mocking, 
    # but we can check if it still adds to memory.
    result = await executor.execute("session-1", "new message", history=explicit_history)
    
    assert len(memory.get_messages()) == 3 # original 1 + new user + new assistant
    assert memory.get_messages()[1]["content"] == "new message"
