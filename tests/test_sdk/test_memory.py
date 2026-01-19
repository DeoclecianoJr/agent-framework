import pytest
from ai_framework.core.memory import BufferMemory, WindowMemory, MemoryManager

def test_buffer_memory():
    mem = BufferMemory()
    mem.add_message("user", "hi")
    mem.add_message("assistant", "hello")
    messages = mem.get_messages()
    
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "hello"

def test_window_memory():
    # K=1 means 2 messages limit
    mem = WindowMemory(k=1)
    mem.add_message("user", "1")
    mem.add_message("assistant", "2")
    mem.add_message("user", "3")
    
    messages = mem.get_messages()
    assert len(messages) == 2
    assert messages[0]["content"] == "2"
    assert messages[1]["content"] == "3"

def test_memory_clear():
    mem = BufferMemory()
    mem.add_message("user", "hi")
    mem.clear()
    assert len(mem.get_messages()) == 0

def test_memory_manager():
    mem = MemoryManager.create("window", k=2)
    assert isinstance(mem, WindowMemory)
    assert mem.k == 2
    
    with pytest.raises(ValueError, match="Unknown memory strategy"):
        MemoryManager.create("invalid")
