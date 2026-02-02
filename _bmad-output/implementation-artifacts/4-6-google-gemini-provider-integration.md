# Story 4-6: Google Gemini Provider Integration

**Story ID:** 4-6-google-gemini-provider-integration
**Epic:** 4 - LLM Integration & Memory  
**Status:** backlog
**Estimate:** 3 story points
**Created:** 2026-01-16
**Sprint:** To be planned

## User Story

As a developer,
I want to integrate Google Gemini as an LLM provider,
So that I can leverage Google's latest generative AI models in my agents.

## Acceptance Criteria

**Given** I have a valid Google AI API key
**When** I configure Gemini as an LLM provider in YAML
**Then** the framework connects to Gemini API successfully
**And** I can use models like gemini-pro and gemini-pro-vision
**And** Gemini provider follows the same abstraction interface as other providers
**And** Streaming responses work correctly with Gemini models
**And** Function calling / tool use is supported (when available)
**And** Token counting is accurate for Gemini models
**And** Cost tracking reflects Gemini's pricing model
**And** Retry logic and fallback work with Gemini provider
**And** Configuration includes model selection, temperature, and safety settings
**And** Provider health checks verify Gemini API availability

## Business Context

Google Gemini integration provides:
- **Model Diversity**: Access to Google's state-of-the-art models
- **Competitive Pricing**: Potentially lower costs than OpenAI/Anthropic
- **Multimodal Capabilities**: Vision and text understanding
- **Vendor Diversification**: Reduce dependency on single provider
- **Performance Options**: Different model sizes (nano, pro, ultra)

## Technical Requirements

### Core Implementation
- [ ] **Gemini Provider Class**: Implement `GeminiProvider` with LLM abstraction interface
- [ ] **Configuration Support**: YAML parsing and validation for Gemini settings
- [ ] **Chat Completion**: Support gemini-pro model for text generation
- [ ] **Streaming**: Implement streaming responses using Gemini's API
- [ ] **Function Calling**: Support Gemini's function calling feature
- [ ] **Token Counting**: Accurate token usage tracking
- [ ] **Cost Tracking**: Implement Gemini pricing model
- [ ] **Error Handling**: Handle Gemini-specific errors gracefully
- [ ] **Health Checks**: Verify API connectivity and model availability

### Dependencies
```bash
# Required package installation
pip install google-generativeai
```

### Configuration Format
```yaml
# config.yaml
llm:
  providers:
    gemini:
      api_key: ${GOOGLE_AI_API_KEY}
      model: gemini-pro
      temperature: 0.7
      safety_settings: "default"
      max_output_tokens: 2048
      top_p: 0.95
      top_k: 40
```

### Implementation Structure
```python
# ai_framework/integrations/gemini.py
import google.generativeai as genai
from ai_framework.core.llm import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementation."""
    
    def __init__(self, config: dict):
        genai.configure(api_key=config['api_key'])
        self.model = genai.GenerativeModel(config.get('model', 'gemini-pro'))
        self.config = config
        
    async def chat_completion(self, messages: list[dict], **kwargs) -> dict:
        """Generate chat completion using Gemini."""
        # Convert messages to Gemini format
        # Call API
        # Map response to standard format
        pass
        
    async def chat_completion_stream(self, messages: list[dict], **kwargs):
        """Stream chat completion from Gemini."""
        # Implement streaming logic
        pass
        
    def count_tokens(self, text: str) -> int:
        """Count tokens using Gemini's tokenizer."""
        return self.model.count_tokens(text).total_tokens
        
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on Gemini pricing."""
        # As of 2024: gemini-pro is free for limited usage
        # Implement pricing logic based on current rates
        pass
        
    async def health_check(self) -> bool:
        """Verify Gemini API is accessible."""
        try:
            # Simple test request
            response = self.model.generate_content("test")
            return True
        except Exception:
            return False
```

### Response Mapping
```python
# Map Gemini response to standard format
def _map_response(gemini_response) -> dict:
    return {
        "id": gemini_response.id,
        "model": "gemini-pro",
        "content": gemini_response.text,
        "role": "assistant",
        "usage": {
            "prompt_tokens": gemini_response.prompt_tokens,
            "completion_tokens": gemini_response.completion_tokens,
            "total_tokens": gemini_response.total_tokens
        },
        "finish_reason": gemini_response.finish_reason
    }
```

## Testing Requirements

### Unit Tests
```python
# tests/test_sdk/test_gemini_provider.py

def test_gemini_provider_initialization():
    """Test Gemini provider initializes correctly."""
    config = {"api_key": "test-key", "model": "gemini-pro"}
    provider = GeminiProvider(config)
    assert provider.model is not None
    
def test_gemini_chat_completion_mock():
    """Test chat completion with mocked API."""
    # Mock genai.GenerativeModel.generate_content
    # Verify response mapping
    pass
    
def test_gemini_token_counting():
    """Test token counting accuracy."""
    provider = GeminiProvider({"api_key": "test"})
    tokens = provider.count_tokens("Hello, world!")
    assert tokens > 0
    
def test_gemini_cost_calculation():
    """Test cost calculation for Gemini."""
    provider = GeminiProvider({"api_key": "test"})
    cost = provider.calculate_cost(1000, 500)
    assert cost >= 0  # Free tier
```

### Integration Tests (with real API)
```python
# tests/test_sdk/test_gemini_integration.py

@pytest.mark.skipif(not os.getenv("GOOGLE_AI_API_KEY"), reason="No API key")
def test_gemini_real_api():
    """Test Gemini provider with real API."""
    config = {
        "api_key": os.getenv("GOOGLE_AI_API_KEY"),
        "model": "gemini-pro"
    }
    provider = GeminiProvider(config)
    
    messages = [{"role": "user", "content": "Say hello"}]
    response = await provider.chat_completion(messages)
    
    assert response["content"]
    assert response["usage"]["total_tokens"] > 0
```

### E2E Tests
```python
# tests/test_gemini_e2e.py

def test_gemini_via_chat_api(client):
    """Test Gemini provider through Chat API."""
    # Configure Gemini provider in test config
    # Send message to /chat
    # Verify response uses Gemini
    # Check metrics shows Gemini usage
    pass
```

## Validation Tasks

### Manual Testing Checklist:
- [ ] Install google-generativeai package
- [ ] Configure valid Google AI API key
- [ ] Send test message using gemini-pro model
- [ ] Verify streaming works correctly
- [ ] Test function calling (if supported)
- [ ] Verify token counting accuracy
- [ ] Check /metrics endpoint shows Gemini usage
- [ ] Test fallback to other provider if Gemini fails
- [ ] Verify health check detects API issues

### Performance Testing:
- [ ] Measure response latency vs OpenAI/Anthropic
- [ ] Test concurrent requests handling
- [ ] Verify token counting performance

### Security Testing:
- [ ] Ensure API key is not logged or exposed
- [ ] Verify SSL/TLS connection to Gemini API
- [ ] Test API key rotation without downtime

## Documentation Updates

- [ ] Add Gemini configuration example to README
- [ ] Update LLM provider documentation
- [ ] Add troubleshooting guide for common Gemini errors
- [ ] Document Gemini pricing and token limits
- [ ] Create migration guide for users switching to Gemini

## Definition of Done

- [x] GeminiProvider class implemented with full abstraction interface
- [x] Configuration parsing and validation for Gemini settings
- [x] Chat completion works with gemini-pro model
- [x] Streaming responses functional
- [x] Token counting implemented
- [x] Error handling and retry logic working
- [x] Unit tests with mocked Gemini API (≥80% coverage)
- [x] Integration tests with real Gemini API (optional, skippable in CI)
- [x] Documentation updated with Gemini configuration examples
- [x] Health check verifies Gemini API connectivity
- [x] All existing tests still pass (no regressions)
- [x] Code reviewed and approved

## Related Documentation

- [Google Gemini API Docs](https://ai.google.dev/docs)
- [google-generativeai Python SDK](https://pypi.org/project/google-generativeai/)
- [Gemini Pricing](https://ai.google.dev/pricing)
- Story 4-1: LLM Provider Abstraction Layer
- Story 4-2: Multi-Provider Support with Configuration
- Story 4-4: Token Counting & Cost Tracking

## Notes

- Gemini offers free tier for limited usage (good for testing)
- gemini-pro-vision supports image inputs (future enhancement)
- Function calling may have different format than OpenAI
- Consider rate limits: Gemini has different limits than OpenAI
