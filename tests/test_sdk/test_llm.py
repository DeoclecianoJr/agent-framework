import pytest
from ai_framework.llm import get_llm, MockLLM, LLMProvider
from langchain_core.language_models.chat_models import BaseChatModel

def test_get_llm_mock():
    llm = get_llm("mock")
    assert isinstance(llm, LLMProvider)
    assert llm.provider == "mock"

@pytest.mark.asyncio
async def test_mock_llm_chat():
    llm = get_llm("mock")
    response = await llm.chat([{"role": "user", "content": "hello"}])
    assert response["content"] == "mock-response"
    assert response["provider"] == "mock"

def test_llm_provider_initialization():
    llm = LLMProvider(provider="openai", model="gpt-4", api_key="test-key")
    assert llm.provider == "openai"
    assert llm.model == "gpt-4"
    assert llm.api_key == "test-key"

def test_llm_provider_unsupported():
    llm = LLMProvider(provider="invalid")
    with pytest.raises(ValueError, match="Unsupported LLM provider: invalid"):
        llm._get_client()

@pytest.mark.asyncio
async def test_openai_integration_attempt(monkeypatch):
    # This just tests that it tries to initialize the correct client
    llm = LLMProvider(provider="openai", model="gpt-3.5-turbo", api_key="fake-key")
    client = llm._get_client()
    assert isinstance(client, BaseChatModel)
    assert client.__class__.__name__ == "ChatOpenAI"

@pytest.mark.asyncio
async def test_anthropic_integration_attempt():
    llm = LLMProvider(provider="anthropic", model="claude-3-opus", api_key="fake-key")
    client = llm._get_client()
    assert isinstance(client, BaseChatModel)
    assert client.__class__.__name__ == "ChatAnthropic"
