# Story 4-5: Retry Logic & Provider Fallback

**Story ID:** 4-5-retry-logic-provider-fallback
**Epic:** 4 - LLM Integration & Memory  
**Status:** ready-for-dev
**Estimate:** 5 story points (new implementation required)
**Created:** 20-01-2026
**Sprint:** Current

## User Story

As a reliability engineer,
I want robust retry logic with exponential backoff and provider fallback,
So that agents remain responsive despite temporary provider issues.

## Acceptance Criteria

**Given** LLM provider encounters errors or timeouts
**When** an agent makes an LLM request
**Then** failed requests retry up to 3 times with exponential backoff
**And** retry delays follow pattern: 1s, 2s, 4s
**And** after retries exhausted, request falls back to secondary provider
**And** circuit breaker pattern prevents cascading failures
**And** all retry attempts and fallbacks are logged with trace IDs
**And** successful requests reset failure counters

## Business Context

Reliability features are critical for:
- **High Availability**: Maintain service during provider outages
- **User Experience**: Avoid request failures from temporary issues
- **Cost Optimization**: Distribute load across multiple providers
- **SLA Compliance**: Meet uptime requirements for production systems

## Technical Requirements

### Core Implementation
- [ ] **Retry Logic**: Exponential backoff with configurable attempts
- [ ] **Provider Fallback**: Automatic secondary provider switching
- [ ] **Circuit Breaker**: Prevent cascading failures
- [ ] **Failure Tracking**: Monitor provider health status
- [ ] **Configuration**: Environment-based retry/fallback settings
- [ ] **Logging**: Detailed retry/fallback event tracking

### Retry Strategy
```python
# Retry configuration
RETRY_ATTEMPTS = 3
RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds
RETRY_EXCEPTIONS = [TimeoutError, ConnectionError, HTTPError(>=500)]
```

### Provider Fallback
```python
# Provider priority configuration  
PRIMARY_PROVIDER = "openai"
FALLBACK_PROVIDERS = ["anthropic", "azure-openai"]
FALLBACK_TRIGGERS = ["max_retries_exceeded", "circuit_breaker_open"]
```

### Circuit Breaker Pattern
```python
# Circuit breaker settings
FAILURE_THRESHOLD = 5      # failures before opening circuit
TIMEOUT_DURATION = 60      # seconds to wait before retry
SUCCESS_THRESHOLD = 2      # successes needed to close circuit
```

## Current Implementation Status

❌ **NOT IMPLEMENTED** - This is a greenfield implementation.

### Current State Analysis:

1. **Basic LLM Integration** (`ai_framework/llm.py`):
   - ✅ OpenAI provider works reliably
   - ✅ Mock provider for testing
   - ❌ No retry logic on failures
   - ❌ No fallback providers configured
   - ❌ Errors propagate directly to user

2. **Error Handling** (`ai_framework/core/executor.py`):
   - ✅ Basic exception catching exists
   - ❌ No retry attempts
   - ❌ No circuit breaker protection
   - ❌ Limited error context for debugging

3. **Provider Management**:
   - ✅ Single provider selection works
   - ❌ No multi-provider configuration
   - ❌ No provider health monitoring
   - ❌ No automatic failover capabilities

### Implementation Plan:

#### Phase 1: Retry Logic
```python
# ai_framework/core/resilience.py (NEW FILE)
import asyncio
import time
from typing import Any, Callable, List, Optional, Type
from dataclasses import dataclass
import logging

@dataclass
class RetryConfig:
    max_attempts: int = 3
    delay_pattern: List[float] = (1.0, 2.0, 4.0)
    retryable_exceptions: List[Type[Exception]] = None

class RetryManager:
    def __init__(self, config: RetryConfig):
        self.config = config
        
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if not self._is_retryable(e) or attempt == self.config.max_attempts - 1:
                    raise
                
                delay = self.config.delay_pattern[min(attempt, len(self.config.delay_pattern) - 1)]
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                last_exception = e
        
        raise last_exception
```

#### Phase 2: Circuit Breaker
```python
# ai_framework/core/resilience.py (continuation)
from enum import Enum
from datetime import datetime, timedelta

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout_duration: int = 60, success_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise
```

#### Phase 3: Provider Fallback
```python
# ai_framework/core/provider_manager.py (NEW FILE)
from typing import Dict, List, Optional
from ai_framework.llm import BaseLLM, OpenAIProvider, MockProvider

class ProviderManager:
    def __init__(self, provider_configs: Dict[str, Dict]):
        self.providers: Dict[str, BaseLLM] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_managers: Dict[str, RetryManager] = {}
        
        for name, config in provider_configs.items():
            self._initialize_provider(name, config)
    
    async def execute_with_fallback(self, providers: List[str], func_name: str, *args, **kwargs) -> Any:
        """Execute LLM call with provider fallback."""
        last_exception = None
        
        for provider_name in providers:
            try:
                provider = self.providers[provider_name]
                circuit_breaker = self.circuit_breakers[provider_name]
                retry_manager = self.retry_managers[provider_name]
                
                # Execute through circuit breaker and retry logic
                async def provider_call():
                    func = getattr(provider, func_name)
                    return await func(*args, **kwargs)
                
                return await circuit_breaker.call(
                    retry_manager.execute_with_retry, 
                    provider_call
                )
                
            except (CircuitBreakerError, ConnectionError, TimeoutError) as e:
                logging.warning(f"Provider {provider_name} failed: {e}. Trying next provider...")
                last_exception = e
                continue
        
        raise last_exception or Exception("All providers failed")
```

#### Phase 4: Integration
```python
# ai_framework/core/executor.py (modify existing)
class AgentExecutor:
    def __init__(self, llm: BaseLLM, provider_manager: Optional[ProviderManager] = None):
        self.llm = llm
        self.provider_manager = provider_manager or self._create_default_provider_manager()
        
    async def _make_llm_call(self, messages: List[Dict], **kwargs) -> Dict:
        """Make LLM call with fallback and retry."""
        if self.provider_manager:
            providers = self._get_provider_priority()
            return await self.provider_manager.execute_with_fallback(
                providers, "chat", messages, **kwargs
            )
        else:
            # Fallback to direct provider call
            return await self.llm.chat(messages, **kwargs)
```

## Validation Tasks

### Unit Tests Required:
```python
# tests/test_resilience.py
def test_retry_logic_exponential_backoff():
    # Test retry delays: 1s, 2s, 4s
    pass

def test_circuit_breaker_state_transitions():
    # Test closed -> open -> half-open -> closed
    pass

def test_provider_fallback_order():
    # Test primary -> secondary -> tertiary
    pass

def test_failure_recovery():
    # Test success resets failure counters
    pass
```

### Integration Tests:
```python  
# tests/test_provider_fallback_integration.py
def test_end_to_end_fallback():
    # Primary provider fails -> fallback succeeds
    pass

def test_circuit_breaker_integration():
    # Multiple failures -> circuit opens -> requests blocked
    pass
```

### Load Testing:
```python
# tests/test_resilience_load.py
def test_concurrent_requests_with_failures():
    # Verify thread safety and performance
    pass
```

## Implementation Files

### New Files to Create:
- **`ai_framework/core/resilience.py`**: Retry logic and circuit breaker
- **`ai_framework/core/provider_manager.py`**: Multi-provider coordination
- **`tests/test_resilience.py`**: Comprehensive resilience tests
- **`tests/test_provider_fallback.py`**: Provider fallback tests

### Files to Modify:
- **`ai_framework/core/executor.py`**: Integrate resilience features
- **`ai_framework/core/config.py`**: Add resilience configuration
- **`app/main.py`**: Initialize provider manager with multiple providers

### Configuration Files:
- **`.env`**: Add resilience settings
  ```env
  AI_SDK_RETRY_ATTEMPTS=3
  AI_SDK_RETRY_DELAYS="1.0,2.0,4.0"
  AI_SDK_CIRCUIT_BREAKER_THRESHOLD=5
  AI_SDK_FALLBACK_PROVIDERS="openai,anthropic"
  ```

## Definition of Done

- [ ] Retry logic with exponential backoff implemented
- [ ] Circuit breaker pattern prevents cascading failures
- [ ] Provider fallback works automatically  
- [ ] All retry/fallback events are logged with trace IDs
- [ ] Configuration supports multiple deployment environments
- [ ] Success scenarios reset failure counters appropriately
- [ ] Performance impact is minimal (< 10ms overhead)
- [ ] Comprehensive test coverage (>85%)
- [ ] Load testing validates reliability under stress
- [ ] Documentation includes troubleshooting guide

## Dependencies

- **Completed Stories**: 4.1 (LLM Abstraction), 4.2 (Multi-provider Support)
- **External**: Additional LLM provider APIs (Anthropic, Azure)
- **Infrastructure**: Monitoring/alerting system for circuit breaker events

## Configuration Example

```env
# .env configuration
AI_SDK_LLM_PROVIDERS="openai,anthropic"
AI_SDK_PRIMARY_PROVIDER="openai"
AI_SDK_FALLBACK_PROVIDERS="anthropic"

# Retry settings
AI_SDK_RETRY_ATTEMPTS=3
AI_SDK_RETRY_DELAYS="1.0,2.0,4.0"
AI_SDK_RETRY_EXCEPTIONS="TimeoutError,ConnectionError,HTTPError"

# Circuit breaker settings
AI_SDK_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
AI_SDK_CIRCUIT_BREAKER_TIMEOUT_DURATION=60
AI_SDK_CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2

# Provider-specific settings
AI_SDK_OPENAI_API_KEY=sk-...
AI_SDK_ANTHROPIC_API_KEY=sk-ant-...
```

## Notes for Developer

🚨 **Complex Implementation Required** - This is a substantial feature!

**Key Design Principles:**
1. **Fail Fast**: Don't retry non-retryable errors (4xx, authentication)
2. **Preserve Context**: All failures logged with trace IDs for debugging
3. **Graceful Degradation**: System remains functional during partial outages
4. **Configuration**: All behavior configurable for different environments

**Implementation Priority:**
1. **Phase 1**: Basic retry logic (highest ROI)
2. **Phase 2**: Circuit breaker (prevents cascading failures)
3. **Phase 3**: Provider fallback (requires multiple provider configs)
4. **Phase 4**: Performance optimization and monitoring

**Testing Strategy:**
- Use mock providers to simulate failures
- Test all state transitions (circuit breaker)
- Validate timing of retry delays
- Load test concurrent failure scenarios

This story significantly enhances system reliability and is critical for production deployments!