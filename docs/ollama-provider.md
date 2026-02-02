# Ollama Local LLM Provider

## Overview

The Ollama provider enables running local LLM inference using Ollama with models like Phi3, Llama2, Mistral, and others. This provides zero-cost development/testing with full data privacy.

## Features

- ✅ Local inference with phi3:mini and other Ollama models
- ✅ Zero API costs ($0 per request)
- ✅ Full data privacy (no external API calls)
- ✅ Streaming responses
- ✅ Token estimation (word-based approximation)
- ✅ Health checks and model discovery
- ✅ Circuit breaker integration
- ✅ Automatic fallback to cloud providers

## Installation

### 1. Install Ollama

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download from https://ollama.ai/download

### 2. Pull Models

```bash
# Pull phi3:mini (recommended, 3.8B parameters)
ollama pull phi3:mini

# Or other models
ollama pull llama2
ollama pull mistral
ollama pull codellama
```

### 3. Start Ollama Service

```bash
# Service runs on http://localhost:11434 by default
ollama serve
```

### 4. Verify Installation

```bash
# Check service is running
curl http://localhost:11434/api/tags

# Test chat
curl http://localhost:11434/api/chat -d '{
  "model": "phi3:mini",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}'
```

## Configuration

### YAML Configuration (Recommended)

Create or update `config.yaml`:

```yaml
llm:
  # Use Ollama as default provider
  provider: ollama
  model: phi3:mini
  
  # Ollama settings
  ollama:
    base_url: http://localhost:11434
    timeout: 60  # seconds
    num_ctx: 2048  # context window
    temperature: 0.7
  
  # Fallback to cloud if Ollama unavailable
  fallback_sequence:
    - ollama
    - openai
```

### Environment Variables

```bash
export AI_SDK_LLM_PROVIDER=ollama
export AI_SDK_LLM_MODEL=phi3:mini
export AI_SDK_OLLAMA_BASE_URL=http://localhost:11434
export AI_SDK_OLLAMA_TIMEOUT=60
export AI_SDK_OLLAMA_NUM_CTX=2048
```

### Python Code

```python
from ai_framework.llm import get_llm

# Simple usage
llm = get_llm(provider="ollama", model="phi3:mini")

# With custom config
llm = get_llm(
    provider="ollama",
    model="llama2",
    base_url="http://localhost:11434",
    temperature=0.5,
    num_ctx=4096,
    timeout=120
)
```

## Usage Examples

### Basic Chat

```python
from ai_framework.llm import get_llm

llm = get_llm(provider="ollama", model="phi3:mini")

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is Python?"}
]

response = await llm.chat(messages)
print(response["content"])
print(f"Tokens: {response['usage']['total_tokens']}")
print(f"Cost: ${response['usage']['cost']}")  # Always $0
```

### Streaming Responses

```python
from ai_framework.core.llm import OllamaLLM

provider = OllamaLLM(model="phi3:mini")

messages = [{"role": "user", "content": "Write a short poem"}]

async for chunk in provider.chat_stream(messages):
    print(chunk["content"], end="", flush=True)
    if chunk["done"]:
        break
```

### Health Check

```python
provider = OllamaLLM(model="phi3:mini")

if provider.health_check():
    print("✅ Ollama is running and model is ready")
else:
    print("❌ Ollama not available")
```

### List Available Models

```python
provider = OllamaLLM()
models = provider.list_models()
print("Available models:", models)
# ['phi3:mini', 'llama2:7b', 'mistral:latest', ...]
```

### Using with Agent Decorator

```python
from ai_framework.decorators import agent

@agent(
    name="local_assistant",
    llm_provider="ollama",
    llm_model="phi3:mini"
)
async def local_assistant(user_input: str, context: dict) -> str:
    """Assistant powered by local Ollama inference."""
    return f"Processing: {user_input}"

# Execute
result = await local_assistant.execute("Hello!")
print(result["response"])
```

## Model Selection

### Recommended Models

| Model | Size | Use Case | Speed | Quality |
|-------|------|----------|-------|---------|
| **phi3:mini** | 3.8B | General chat, fast iteration | ⚡⚡⚡ | ⭐⭐⭐ |
| llama2 | 7B | Better quality responses | ⚡⚡ | ⭐⭐⭐⭐ |
| mistral | 7B | Code and technical tasks | ⚡⚡ | ⭐⭐⭐⭐ |
| codellama | 7B/13B | Code generation | ⚡⚡ | ⭐⭐⭐⭐⭐ |

### Switch Models

```python
# Development: fast iteration
llm_dev = get_llm(provider="ollama", model="phi3:mini")

# Testing: better quality
llm_test = get_llm(provider="ollama", model="llama2")

# Production: cloud provider
llm_prod = get_llm(provider="openai", model="gpt-4o-mini")
```

## Error Handling

### Ollama Not Running

```python
try:
    response = await llm.chat(messages)
except Exception as e:
    if "Cannot connect to Ollama" in str(e):
        print("❌ Ollama service not running")
        print("Start with: ollama serve")
    else:
        raise
```

### Model Not Available

```python
provider = OllamaLLM(model="nonexistent-model")

if not provider.health_check():
    print("Model not available. Pull it with:")
    print(f"  ollama pull {provider.model}")
    
    # Show available models
    available = provider.list_models()
    print(f"Available: {available}")
```

### Automatic Fallback

Configure fallback in `config.yaml`:

```yaml
llm:
  default_provider: ollama
  fallback_sequence:
    - ollama      # Try local first
    - openai      # Fallback to cloud
```

If Ollama fails, the system automatically uses OpenAI.

## Performance Tuning

### Context Window

```python
# Smaller context = faster
llm_fast = get_llm(provider="ollama", model="phi3:mini", num_ctx=1024)

# Larger context = more memory, slower
llm_large = get_llm(provider="ollama", model="phi3:mini", num_ctx=4096)
```

### Temperature

```python
# Deterministic output
llm = get_llm(provider="ollama", model="phi3:mini", temperature=0.0)

# Creative output
llm = get_llm(provider="ollama", model="phi3:mini", temperature=0.9)
```

### Timeout

```python
# Short timeout for simple queries
llm = get_llm(provider="ollama", model="phi3:mini", timeout=30)

# Longer for complex reasoning
llm = get_llm(provider="ollama", model="phi3:mini", timeout=120)
```

## Token Counting

Ollama doesn't expose exact token counts, so we use word-based estimation:

**Formula:** `tokens ≈ words / 0.75`

```python
provider = OllamaLLM()

text = "Hello world, how are you?"
tokens = provider._count_tokens(text)
# Returns: ~7 tokens (5 words / 0.75)
```

This is approximate but sufficient for development/testing.

## Cost Tracking

All Ollama requests have **$0 cost**:

```python
response = await llm.chat(messages)
print(response["usage"])
# {
#   "prompt_tokens": 10,
#   "completion_tokens": 50,
#   "total_tokens": 60,
#   "cost": 0.0  # ✅ Always zero
# }
```

Perfect for:
- Development/testing without budget concerns
- CI/CD pipelines
- Educational projects
- Privacy-sensitive applications

## Limitations

1. **No Exact Token Counts**
   - Word-based estimation (approximate)
   - Use cloud providers for production cost tracking

2. **Function Calling**
   - Depends on model support
   - Not all models support tools/functions
   - May need manual tool parsing

3. **Context Window**
   - Limited by model (phi3:mini = 4K tokens)
   - Cloud models have larger windows (128K+)

4. **Performance**
   - Depends on local hardware (GPU/CPU)
   - Slower than cloud APIs on weak machines
   - Fast with GPU acceleration

5. **Model Availability**
   - Must manually pull models (`ollama pull`)
   - Models can be large (GBs of disk space)

## Troubleshooting

### Ollama Not Found

```bash
# Check if installed
which ollama

# Install if missing
curl -fsSL https://ollama.ai/install.sh | sh
```

### Service Not Running

```bash
# Start Ollama service
ollama serve

# Or run in background
ollama serve &
```

### Model Not Pulled

```bash
# List pulled models
ollama list

# Pull missing model
ollama pull phi3:mini
```

### Connection Refused

```bash
# Check service is listening
curl http://localhost:11434/api/tags

# Check firewall
sudo ufw status
```

### Slow Responses

- Use GPU if available
- Reduce context window (`num_ctx=1024`)
- Use smaller model (phi3:mini vs llama2:70b)
- Check CPU/memory usage

## Comparison: Ollama vs Cloud

| Feature | Ollama | OpenAI | Anthropic |
|---------|--------|--------|-----------|
| **Cost** | $0 | $0.0015/1K | $0.015/1K |
| **Privacy** | ✅ Local | ❌ Cloud | ❌ Cloud |
| **Speed** | Varies | ⚡⚡⚡ | ⚡⚡⚡ |
| **Quality** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Context** | 4K-32K | 128K+ | 200K+ |
| **Setup** | Manual | API Key | API Key |
| **Offline** | ✅ Yes | ❌ No | ❌ No |

**When to Use Ollama:**
- Development and testing
- Privacy-sensitive data
- Offline environments
- Learning/experimentation
- CI/CD pipelines

**When to Use Cloud:**
- Production workloads
- High-quality responses needed
- Large context windows
- Latest model capabilities

## API Reference

### OllamaLLM

```python
from ai_framework.core.llm import OllamaLLM

provider = OllamaLLM(
    model="phi3:mini",           # Model name
    base_url="http://localhost:11434",  # Ollama API URL
    temperature=0.7,             # Sampling temperature
    num_ctx=2048,                # Context window size
    timeout=60                   # Request timeout (seconds)
)
```

**Methods:**

- `chat(messages, **kwargs)` - Generate completion
- `chat_stream(messages, **kwargs)` - Stream completion
- `health_check()` - Check service and model availability
- `list_models()` - List available models
- `_count_tokens(text)` - Estimate token count

### LLMProvider with Ollama

```python
from ai_framework.llm import get_llm

llm = get_llm(
    provider="ollama",
    model="phi3:mini",
    base_url="http://localhost:11434",
    timeout=60,
    num_ctx=2048
)

response = await llm.chat(messages)
```

## Integration Testing

### Skip Tests if Ollama Not Running

```python
import pytest
import requests

def is_ollama_running():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except:
        return False

@pytest.mark.skipif(not is_ollama_running(), reason="Ollama not running")
async def test_ollama_integration():
    llm = get_llm(provider="ollama", model="phi3:mini")
    response = await llm.chat([{"role": "user", "content": "Hi"}])
    assert response["content"]
```

## Further Resources

- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama Models Library](https://ollama.ai/library)
- [Phi3 Model Card](https://ollama.ai/library/phi3)
- [Local LLM Best Practices](https://github.com/ollama/ollama#best-practices)

## Next Steps

1. Try different models for your use case
2. Optimize context window and temperature
3. Configure fallback to cloud providers
4. Set up GPU acceleration for faster inference
5. Monitor local resource usage (CPU/RAM/GPU)

