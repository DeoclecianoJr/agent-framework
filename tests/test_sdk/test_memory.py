import pytest
from ai_framework.core.memory import BufferMemory, WindowMemory, MemoryManager

@pytest.mark.asyncio
async def test_buffer_memory():
    mem = BufferMemory()
    await mem.add_message("user", "hi")
    await mem.add_message("assistant", "hello")
    messages = await mem.get_messages()
    
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "hello"

@pytest.mark.asyncio
async def test_window_memory():
    # K=1 means 2 messages limit
    mem = WindowMemory(k=1)
    await mem.add_message("user", "1")
    await mem.add_message("assistant", "2")
    await mem.add_message("user", "3")
    
    messages = await mem.get_messages()
    assert len(messages) == 2
    assert messages[0]["content"] == "2"
    assert messages[1]["content"] == "3"

@pytest.mark.asyncio
async def test_memory_clear():
    mem = BufferMemory()
    await mem.add_message("user", "hi")
    await mem.clear()
    assert len(await mem.get_messages()) == 0

def test_memory_manager():
    mem = MemoryManager.create("window", k=2)
    assert isinstance(mem, WindowMemory)
    assert mem.k == 2
    
    with pytest.raises(ValueError, match="Unknown memory strategy"):
        MemoryManager.create("invalid")
