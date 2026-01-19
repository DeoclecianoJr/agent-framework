"""Resilience utilities for external service calls.

Provides retry with exponential backoff and circuit breaker patterns.
"""
import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Raised when the circuit is open."""
    pass


class CircuitBreaker:
    """Basic implementation of the Circuit Breaker pattern."""

    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 30,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def record_success(self):
        """Record a successful call."""
        self.failures = 0
        self.state = "CLOSED"
        self.last_failure_time = None

    def record_failure(self):
        """Record a failed call."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit Breaker '{self.name}' is now OPEN due to {self.failures} failures")

    def can_execute(self) -> bool:
        """Check if the call can be executed."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Check for recovery timeout
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info(f"Circuit Breaker '{self.name}' is now HALF-OPEN")
                return True
            return False
            
        return True  # HALF-OPEN


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], tuple] = Exception,
    **kwargs
) -> Any:
    """Retry an async function with exponential backoff.
    
    Args:
        func: The async function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Factor to multiply delay by each retry
        exceptions: Exception types to catch and retry on
        **kwargs: Arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        The last exception encountered after max retries
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(**kwargs)
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"Failed after {max_retries} retries: {e}")
                break
                
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s due to: {e}")
            await asyncio.sleep(delay)
            delay *= backoff_factor
            
    raise last_exception


def resilience_decorator(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    circuit_breaker: Optional[CircuitBreaker] = None
):
    """Decorator for adding resilience to async methods."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if circuit_breaker and not circuit_breaker.can_execute():
                raise CircuitBreakerError(f"Circuit breaker '{circuit_breaker.name}' is open")
                
            try:
                result = await retry_with_backoff(
                    lambda **kw: func(*args, **kw),
                    max_retries=max_retries,
                    initial_delay=initial_delay,
                    **kwargs
                )
                if circuit_breaker:
                    circuit_breaker.record_success()
                return result
            except Exception as e:
                if circuit_breaker:
                    circuit_breaker.record_failure()
                raise e
        return wrapper
    return decorator
