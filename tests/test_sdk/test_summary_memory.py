import pytest
from unittest.mock import AsyncMock
from ai_framework.core.memory import SummaryMemory

@pytest.mark.asyncio
async def test_summary_memory_summarization():
    llm = AsyncMock()
    llm.chat.return_value = {"content": "This is a summary of the first two messages.", "role": "assistant"}
    
    # max_messages=2 means it will summarize when the 3rd message is added
    mem = SummaryMemory(llm=llm, max_messages=2)
    
    await mem.add_message("user", "Hello")
    await mem.add_message("assistant", "Hi there!")
    
    # Still 2 messages
    msgs = await mem.get_messages()
    assert len(msgs) == 2
    assert llm.chat.call_count == 0
    
    # Adding 3rd message triggers summarization.
    # New logic: summarizes EVERYTHING currently in the buffer.
    await mem.add_message("user", "How are you?")
    
    # Now it should have: 1 summary message + 0 remaining messages in buffer (as it was cleared after summary)
    # WAIT: Actually in my updated _summarize, I check length > max_messages AFTER adding.
    # So if max_messages=2 and I add the 3rd, it summarizes the 3 and clears the buffer.
    msgs = await mem.get_messages()
    assert len(msgs) == 1
    assert "Resumo do contexto" in msgs[0]["content"] or "Context summary" in msgs[0]["content"]
    assert llm.chat.call_count == 1
    assert mem.summary_updated is True

@pytest.mark.asyncio
async def test_summary_memory_clear():
    llm = AsyncMock()
    mem = SummaryMemory(llm=llm, max_messages=2)
    await mem.add_message("user", "hi")
    mem.summary = "old summary"
    
    await mem.clear()
    msgs = await mem.get_messages()
    assert len(msgs) == 0
    assert mem.summary is None
