import pytest
from ai_framework.core.guardrails import GuardrailProcessor, GuardrailViolation
from ai_framework.core.executor import AgentExecutor
from ai_framework.llm import MockLLM


def test_blocklist_filters_content():
    processor = GuardrailProcessor(blocklist=["competidores", "financeiro"])
    
    # Valid input
    processor.validate_input("Como está o tempo?")
    
    # Blocked input
    with pytest.raises(GuardrailViolation) as excinfo:
        processor.validate_input("Fale sobre nossos competidores")
    assert "competidores" in str(excinfo.value)
    assert excinfo.value.topic == "competidores"


def test_allowlist_filters_content():
    processor = GuardrailProcessor(allowlist=["ajuda", "suporte"])
    
    # Allowed input
    processor.validate_input("Eu preciso de ajuda")
    
    # Not allowed input
    with pytest.raises(GuardrailViolation) as excinfo:
        processor.validate_input("Como vai você?")
    assert "allowed topics" in str(excinfo.value)


def test_confidence_threshold_fallback():
    processor = GuardrailProcessor(min_confidence=0.8)
    
    output = "Aqui está sua resposta"
    
    # High confidence
    assert processor.validate_output(output, confidence=0.9) == output
    
    # Low confidence
    fallback = processor.validate_output(output, confidence=0.5)
    assert "não tenho certeza" in fallback
    assert fallback != output


@pytest.mark.asyncio
async def test_executor_with_guardrails_input_blocking():
    llm = MockLLM(response_text="Ignorado")
    processor = GuardrailProcessor(blocklist=["segredo"])
    executor = AgentExecutor(llm=llm, guardrails=processor)
    
    result = await executor.execute(session_id="test", message_content="Diga o segredo")
    
    assert "não posso ajudar" in result["content"]
    assert "Bloqueado: segredo" in result["content"]
    assert result["metadata"]["guardrail_violation"] is True
    assert result["metadata"]["topic"] == "segredo"


@pytest.mark.asyncio
async def test_executor_with_guardrails_output_fallback():
    # Mock LLM that returns low confidence if we simulate it via metadata
    class LowConfidenceLLM(MockLLM):
        async def chat(self, messages, **kwargs):
            resp = await super().chat(messages, **kwargs)
            # Metadata is now guaranteed to exist due to our fix in llm.py
            resp["metadata"]["confidence"] = 0.4
            return resp
            
    llm = LowConfidenceLLM(response_text="Resposta incerta")
    processor = GuardrailProcessor(min_confidence=0.7)
    executor = AgentExecutor(llm=llm, guardrails=processor)
    
    result = await executor.execute(session_id="test", message_content="Pergunta difícil")
    
    assert "não tenho certeza" in result["content"]
    assert "incerta" not in result["content"]


def test_guardrail_configs_from_dict():
    config = {
        "guardrails": {
            "blocklist": ["bad"],
            "allowlist": ["good"],
            "min_confidence": 0.5
        }
    }
    processor = GuardrailProcessor.from_config(config)
    assert "bad" in processor.blocklist
    assert "good" in processor.allowlist
    assert processor.min_confidence == 0.5
