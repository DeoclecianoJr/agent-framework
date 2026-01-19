import pytest
from ai_framework.core.executor import AgentExecutor
from ai_framework.llm import MockLLM

@pytest.mark.asyncio
async def test_executor_masks_pii():
    mock_llm = MockLLM()
    executor = AgentExecutor(llm=mock_llm)
    
    # We want to verify that the message sent to LLM is masked
    # But executor returns the LLM response, not what it sent.
    # We can check memory if it's enabled, or mock llm.chat
    
    import unittest.mock as mock
    with mock.patch.object(executor.llm, "chat", wraps=executor.llm.chat) as mock_chat:
        await executor.execute(
            session_id="test-session",
            message_content="My email is secret@example.com",
            mask_pii=True
        )
        
        # Check first call to chat
        args, kwargs = mock_chat.call_args
        messages = args[0]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert user_msg["content"] == "My email is [REDACTED]"
        assert "secret@example.com" not in user_msg["content"]

@pytest.mark.asyncio
async def test_executor_does_not_mask_pii_by_default():
    mock_llm = MockLLM()
    executor = AgentExecutor(llm=mock_llm)
    
    import unittest.mock as mock
    with mock.patch.object(executor.llm, "chat", wraps=executor.llm.chat) as mock_chat:
        await executor.execute(
            session_id="test-session",
            message_content="My email is secret@example.com",
            mask_pii=False
        )
        
        args, kwargs = mock_chat.call_args
        messages = args[0]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert user_msg["content"] == "My email is secret@example.com"
