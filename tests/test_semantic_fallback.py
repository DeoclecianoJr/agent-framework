import pytest
from unittest.mock import AsyncMock, MagicMock
from ai_framework.core.executor import AgentExecutor
from ai_framework.core.guardrails import GuardrailProcessor, GuardrailViolation

@pytest.mark.asyncio
async def test_semantic_fallback_success():
    """Test that a message failing regex keyword check passes via semantic LLM check."""
    from ai_framework.core.config import settings
    
    # Enable guardrails for this test and disable global themes
    original_guardrails_enabled = settings.guardrails_enabled
    original_default_themes = settings.default_allowed_themes
    settings.guardrails_enabled = True
    settings.default_allowed_themes = []  # Disable global themes
    
    try:
        llm = AsyncMock()
        # First response: Yes (for semantic check), Second response: normal answer
        llm.chat.side_effect = [
            {"content": "Yes", "role": "assistant"},
            {"content": "Aqui estão as instruções para VPN...", "role": "assistant"}
        ]
        
        executor = AgentExecutor(llm=llm)
        processor = GuardrailProcessor(allowed_themes=["marketing"])  # Use tema que não está nos defaults
        
        # "Como acesso a rede interna?" doesn't contain "marketing" but semantic check says yes
        response = await executor.execute(
            session_id="test-session",
            message_content="Como acesso a rede interna?",
            guardrails=processor
        )
        
        # Assertions
        assert response["metadata"].get("guardrail_violation") in [False, None]
        assert "VPN" in response["content"]
        # Verify llm.chat was called twice (once for check, once for answer)
        assert llm.chat.call_count == 2
    finally:
        # Restore original values
        settings.guardrails_enabled = original_guardrails_enabled
        settings.default_allowed_themes = original_default_themes
    
    # Check first call was the semantic check
    check_messages = llm.chat.call_args_list[0][0][0]
    assert "related to" in check_messages[0]["content"]
    assert "marketing" in check_messages[0]["content"]

@pytest.mark.asyncio
async def test_semantic_fallback_failure():
    """Test that a message failing both regex and semantic check is blocked."""
    from ai_framework.core.config import settings
    
    # Enable guardrails for this test and disable global themes
    original_guardrails_enabled = settings.guardrails_enabled
    original_default_themes = settings.default_allowed_themes
    settings.guardrails_enabled = True
    settings.default_allowed_themes = []  # Disable global themes
    
    try:
        llm = AsyncMock()
        # LLM says "No" to the semantic check
        llm.chat.side_effect = [
            {"content": "No", "role": "assistant"}
        ]
        
        executor = AgentExecutor(llm=llm)
        processor = GuardrailProcessor(allowed_themes=["marketing"])  # Use tema que não está nos defaults
        
        # Definitely off-topic
        response = await executor.execute(
            session_id="test-session",
            message_content="Qual a melhor receita de bolo?",
            guardrails=processor
        )
        
        # Assertions
        assert response["metadata"].get("guardrail_violation") is True
        assert "assunto principal" in response["content"]
        # Only called once for the check
        assert llm.chat.call_count == 1
    finally:
        # Restore original values
        settings.guardrails_enabled = original_guardrails_enabled
        settings.default_allowed_themes = original_default_themes
