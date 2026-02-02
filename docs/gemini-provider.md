# Google Gemini Provider Integration

## Overview

The AI Framework now supports Google Gemini as an LLM provider. This integration allows you to use Google's latest generative AI models (gemini-pro, gemini-1.5-pro, gemini-pro-vision) in your agents.

## Prerequisites

1. **Install the google-generativeai package** (already included):
   ```bash
   pip install google-generativeai
   ```

2. **Get a Google AI API Key**:
   - Go to [Google AI Studio](https://aistudio.google.com)
   - Sign in with your Google account
   - Click "Get API Key" and create a new key
   - Copy the API key

## Configuration

### Via Environment Variable

Set the `GOOGLE_API_KEY` environment variable:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

### Via YAML Configuration

Create a `config.yaml` file in your project:

```yaml
llm:
  provider: gemini
  model: gemini-pro
  
  # Gemini-specific settings
  google_api_key: ${GOOGLE_API_KEY}
  gemini_temperature: 0.7
  gemini_max_output_tokens: 2048
  gemini_top_p: 0.95
  gemini_top_k: 40
```

### Via Python

```python
from ai_framework.core.llm import LLMProvider

provider = LLMProvider(
    provider="gemini",
    model="gemini-pro",
    api_key="your-api-key",
    temperature=0.7
)
```

## Supported Models

### gemini-pro
- **Description**: Latest general-purpose model
- **Pricing**: Free tier (1M tokens/day limit)
- **Best for**: General text generation, Q&A, summarization
- **Limitations**: Text only, no vision capability

### gemini-pro-vision
- **Description**: Vision-capable model for multimodal understanding
- **Pricing**: $0.00125/1k input tokens, $0.00375/1k output tokens
- **Best for**: Image analysis, OCR, visual question answering
- **Features**: Process images and text together

### gemini-1.5-pro
- **Description**: Latest high-capability model
- **Pricing**: $1.25/1M input tokens, $2.50/1M output tokens
- **Best for**: Complex reasoning, long documents, multi-turn conversations
- **Advantages**: Larger context window, better reasoning

### gemini-1.5-flash
- **Description**: Fast, lightweight model
- **Pricing**: $0.075/1M input tokens, $0.3/1M output tokens
- **Best for**: Quick responses, high-volume inference
- **Advantages**: Faster response times, lower cost

## Usage Examples

### Basic Chat

```python
import asyncio
from ai_framework.core.llm import LLMProvider

async def main():
    provider = LLMProvider(
        provider="gemini",
        model="gemini-pro",
        api_key="your-api-key"
    )
    
    messages = [
        {"role": "user", "content": "What is machine learning?"}
    ]
    
    response = await provider.chat(messages)
    print(response["content"])
    print(f"Tokens used: {response['usage']['total_tokens']}")
    print(f"Cost: ${response['usage']['cost']}")

asyncio.run(main())
```

### Streaming Responses

```python
import asyncio
from ai_framework.core.llm import LLMProvider

async def main():
    provider = LLMProvider(
        provider="gemini",
        model="gemini-pro",
        api_key="your-api-key"
    )
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a short poem about AI"}
    ]
    
    async for chunk in provider.chat_stream(messages):
        print(chunk["content"], end="", flush=True)
    
    print()

asyncio.run(main())
```

### Custom Generation Parameters

```python
import asyncio
from ai_framework.core.llm import LLMProvider

async def main():
    provider = LLMProvider(
        provider="gemini",
        model="gemini-pro"
    )
    
    messages = [{"role": "user", "content": "Be creative!"}]
    
    response = await provider.chat(
        messages,
        temperature=0.9,  # More creative
        max_output_tokens=500,
        top_p=0.8,
        top_k=50
    )
    
    print(response["content"])

asyncio.run(main())
```

### Using with Agents

```python
from ai_framework.decorators import agent
from ai_framework.core.llm import LLMProvider

@agent(
    name="ai-assistant",
    description="General AI assistant",
    provider="gemini",
    model="gemini-pro",
    api_key="your-api-key"
)
def my_agent(user_input: str) -> str:
    """Process user input with Gemini."""
    # Your agent logic here
    return user_input

# The agent will use Gemini for LLM calls
response = my_agent("Hello, how can you help me?")
print(response)
```

## Configuration Parameters

### Core Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model` | `gemini-pro` | Model name to use |
| `api_key` | From env | Google AI API key |
| `temperature` | `0.7` | Sampling temperature (0.0-1.0) |

### Advanced Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_output_tokens` | `2048` | Maximum tokens to generate |
| `top_p` | `0.95` | Nucleus sampling parameter |
| `top_k` | `40` | Top-k sampling parameter |
| `safety_settings` | `None` | Safety filter settings |

## Pricing

### Free Tier
- **gemini-pro**: 1M tokens/day free
- No credit card required
- Perfect for development and testing

### Paid Tier
| Model | Input | Output |
|-------|-------|--------|
| gemini-pro | Free | Free |
| gemini-pro-vision | $0.00125/1k | $0.00375/1k |
| gemini-1.5-pro | $1.25/1M | $2.50/1M |
| gemini-1.5-flash | $0.075/1M | $0.3/1M |

**Note**: Prices are approximate as of 2024. Check [Gemini Pricing](https://ai.google.dev/pricing) for current rates.

## Token Counting

The framework automatically counts tokens using Gemini's tokenizer:

```python
from ai_framework.core.llm import GeminiLLM

provider = GeminiLLM(api_key="your-api-key")

tokens = provider._count_tokens("Your text here")
print(f"Tokens: {tokens}")
```

## Health Checks

Verify Gemini API connectivity:

```python
from ai_framework.core.llm import GeminiLLM

provider = GeminiLLM(api_key="your-api-key")

if provider.health_check():
    print("Gemini API is accessible")
else:
    print("Gemini API is unavailable")
```

## Error Handling

### Invalid API Key

```python
try:
    provider = GeminiLLM(api_key="invalid-key")
    response = await provider.chat([{"role": "user", "content": "Hi"}])
except ValueError as e:
    print(f"API key error: {e}")
except Exception as e:
    print(f"Request failed: {e}")
```

### Rate Limiting

Gemini enforces rate limits. The framework includes automatic retry logic with exponential backoff:

```python
# Automatically retries up to 3 times with backoff
provider = LLMProvider(
    provider="gemini",
    model="gemini-pro"
)

response = await provider.chat(messages)  # Auto-retries on rate limit
```

### Network Errors

```python
try:
    response = await provider.chat(messages)
except Exception as e:
    print(f"Network error: {e}")
    # Implement fallback logic
```

## Listing Available Models

```python
from ai_framework.core.llm import GeminiLLM

provider = GeminiLLM(api_key="your-api-key")
models = provider.list_models()

for model in models:
    print(model)
```

## Troubleshooting

### "Google API key not provided"
- **Cause**: Missing API key
- **Solution**: Set `GOOGLE_API_KEY` environment variable or pass `api_key` parameter

### "google-generativeai not installed"
- **Cause**: Package not installed
- **Solution**: `pip install google-generativeai`

### "Failed to initialize Gemini"
- **Cause**: API key invalid or network issue
- **Solution**: Check API key validity, verify internet connection

### Rate Limiting (429 errors)
- **Cause**: Too many requests in short time
- **Solution**: Framework auto-retries; consider increasing delay between requests

### Token Counting Fails
- **Cause**: API unavailable temporarily
- **Solution**: Uses fallback word-based estimation (1 token ≈ 0.33 words)

## Cost Monitoring

Track costs across requests:

```python
response = await provider.chat(messages)

cost = response["usage"]["cost"]
tokens = response["usage"]["total_tokens"]

print(f"Tokens: {tokens}")
print(f"Cost: ${cost:.6f}")
```

## Comparing with Other Providers

```python
import asyncio
from ai_framework.core.llm import LLMProvider

async def compare():
    providers = {
        "openai": {"provider": "openai", "model": "gpt-3.5-turbo"},
        "anthropic": {"provider": "anthropic", "model": "claude-3-haiku"},
        "gemini": {"provider": "gemini", "model": "gemini-pro"},
    }
    
    message = [{"role": "user", "content": "Hello"}]
    
    for name, config in providers.items():
        provider = LLMProvider(**config)
        response = await provider.chat(message)
        print(f"{name}: {response['content'][:50]}... (Cost: ${response['usage']['cost']})")

asyncio.run(compare())
```

## Best Practices

1. **Use environment variables for API keys**:
   ```bash
   export GOOGLE_API_KEY="your-key"
   ```

2. **Set appropriate temperature**:
   - `0.0-0.3`: Deterministic responses (good for Q&A)
   - `0.5-0.7`: Balanced (general use)
   - `0.8-1.0`: Creative (brainstorming)

3. **Monitor costs**:
   - Log token usage and costs
   - Set up alerts for unexpected usage

4. **Use streaming for long responses**:
   ```python
   async for chunk in provider.chat_stream(messages):
       # Process chunks in real-time
   ```

5. **Implement fallback providers**:
   ```python
   try:
       response = await gemini_provider.chat(messages)
   except Exception:
       response = await openai_provider.chat(messages)
   ```

## Integration with Agents

```python
from ai_framework.decorators import agent, tool
from ai_framework.core.llm import LLMProvider

@agent(
    name="research-agent",
    description="AI research assistant",
    provider="gemini",
    model="gemini-1.5-pro"  # Use better model for complex tasks
)
def research_agent(query: str):
    """Multi-turn research capability."""
    return query

@tool
def search_web(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

@tool
def summarize(text: str) -> str:
    """Summarize text."""
    return f"Summary: {text[:100]}..."
```

## Advanced Configuration

### Safety Settings

```python
from ai_framework.core.llm import LLMProvider
import google.generativeai as genai

provider = LLMProvider(provider="gemini", model="gemini-pro")

safety_settings = [
    {
        "category": genai.types.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
        "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
    }
]

response = await provider.chat(
    messages,
    safety_settings=safety_settings
)
```

## Migration Guide

### From OpenAI to Gemini

```python
# Before (OpenAI)
provider = LLMProvider(
    provider="openai",
    model="gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY")
)

# After (Gemini)
provider = LLMProvider(
    provider="gemini",
    model="gemini-pro",
    api_key=os.getenv("GOOGLE_API_KEY")
)

# Rest of code stays the same!
response = await provider.chat(messages)
```

### From Anthropic to Gemini

```python
# Before (Anthropic)
provider = LLMProvider(
    provider="anthropic",
    model="claude-3-haiku",
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# After (Gemini)
provider = LLMProvider(
    provider="gemini",
    model="gemini-1.5-flash",  # Similar speed/cost
    api_key=os.getenv("GOOGLE_API_KEY")
)

# Identical usage!
response = await provider.chat(messages)
```

## References

- [Google AI Studio](https://aistudio.google.com)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Google Generative AI Python Library](https://github.com/google-gemini/generative-ai-python)
- [Gemini Pricing](https://ai.google.dev/pricing)

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test cases in `tests/test_gemini_provider.py`
3. Check example scripts in `examples/`
4. Open an issue on GitHub
