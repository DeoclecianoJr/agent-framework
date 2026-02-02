import pytest
from ai_framework.core.guardrails import GuardrailProcessor, GuardrailViolation
from ai_framework.core.executor import AgentExecutor
from ai_framework.llm import MockLLM

def test_guardrail_theme_enforcement_missing_theme():
    """Test that GuardrailProcessor raises GuardrailViolation when theme is missing."""
    processor = GuardrailProcessor(allowed_themes=["suporte", "tech"])
    
    # Off-topic message
    with pytest.raises(GuardrailViolation) as excinfo:
        processor.validate_input("Como está o tempo hoje?")
    
    assert "assunto principal" in str(excinfo.value)
    assert excinfo.value.topic == "off-topic"

def test_guardrail_theme_enforcement_matching_theme():
    """Test that GuardrailProcessor allows messages matching the theme."""
    processor = GuardrailProcessor(allowed_themes=["suporte", "tech"])
    
    # On-topic message
    processor.validate_input("Preciso de suporte técnico") # Should not raise

def test_guardrail_allows_neutral_greetings():
    """Test that neutral greetings are allowed even if they don't match theme."""
    processor = GuardrailProcessor(allowed_themes=["suporte", "tech"])
    
    # Neutral greeting
    processor.validate_input("Olá, tudo bem?") # Should not raise
    processor.validate_input("Bom dia") # Should not raise
    processor.validate_input("Obrigado") # Should not raise

@pytest.mark.asyncio
async def test_executor_with_dynamic_theme():
    """Test AgentExecutor blocks off-topic messages via dynamic themes in kwargs."""
    from ai_framework.core.config import settings
    
    # Enable guardrails and disable global themes for this test
    original_guardrails_enabled = settings.guardrails_enabled
    original_default_themes = settings.default_allowed_themes
    settings.guardrails_enabled = True
    settings.default_allowed_themes = []  # Disable global themes
    
    try:
        llm = MockLLM()
        executor = AgentExecutor(llm=llm)
        
        # 1. Message that should be blocked
        response = await executor.execute(
            session_id="test",
            message_content="Quero falar sobre futebol",
            guardrails=GuardrailProcessor(),
            allowed_themes=["IA", "Framework"]
        )
        
        assert response["metadata"]["guardrail_violation"] is True
        assert "assunto principal" in response["content"]

        # 2. Message that should pass
        response = await executor.execute(
            session_id="test",
            message_content="Me fale sobre o Framework",
            guardrails=GuardrailProcessor(),
            allowed_themes=["IA", "Framework"]
        )
        
        assert response["metadata"].get("guardrail_violation") is False
        assert response["role"] == "assistant"
    finally:
        # Restore original values
        settings.guardrails_enabled = original_guardrails_enabled
        settings.default_allowed_themes = original_default_themes

@pytest.mark.asyncio
async def test_llm_guardrail_prompt_injection():
    """Test that the executor correctly injects theme rules into the system prompt."""
    from unittest.mock import AsyncMock
    llm = MockLLM()
    llm.chat = AsyncMock(return_value={
        "content": "Solo temas permitidos!",
        "role": "assistant",
        "usage": {"total_tokens": 0},
        "metadata": {}
    })
    
    executor = AgentExecutor(llm=llm)
    processor = GuardrailProcessor(allowed_themes=["tech", "support"])
    
    await executor.execute(
        session_id="test",
        message_content="Olá",
        guardrails=processor
    )
    
    # Get the last call to llm.chat
    called_messages = llm.chat.call_args[0][0]
    system_msg = next(m for m in called_messages if m["role"] == "system")
    
    assert "CRITICAL SAFETY RULE" in system_msg["content"]
    assert "tech" in system_msg["content"]
    assert "support" in system_msg["content"]
