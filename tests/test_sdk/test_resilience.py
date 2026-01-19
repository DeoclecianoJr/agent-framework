import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from ai_framework.core.resilience import retry_with_backoff, CircuitBreaker, CircuitBreakerError


@pytest.mark.asyncio
async def test_retry_with_backoff_success():
    mock_func = AsyncMock(return_value="success")
    result = await retry_with_backoff(mock_func, max_retries=3, initial_delay=0.1)
    assert result == "success"
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_retry_with_backoff_fails_then_succeeds():
    mock_func = AsyncMock()
    mock_func.side_effect = [ValueError("fail"), ValueError("fail"), "success"]
    
    result = await retry_with_backoff(mock_func, max_retries=3, initial_delay=0.1)
    assert result == "success"
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_exhausted():
    mock_func = AsyncMock(side_effect=ValueError("constant fail"))
    
    with pytest.raises(ValueError, match="constant fail"):
        await retry_with_backoff(mock_func, max_retries=2, initial_delay=0.1)
    
    assert mock_func.call_count == 3  # Initial + 2 retries


def test_circuit_breaker_logic():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    assert cb.can_execute() is True
    
    # 1st failure
    cb.record_failure()
    assert cb.state == "CLOSED"
    assert cb.can_execute() is True
    
    # 2nd failure - should OPEN
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.can_execute() is False
    
    # Still open
    assert cb.can_execute() is False


@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.2)
    
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.can_execute() is False
    
    # Wait for recovery timeout
    await asyncio.sleep(0.3)
    
    assert cb.can_execute() is True
    assert cb.state == "HALF-OPEN"
    
    # Success in half-open should close it
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.can_execute() is True

