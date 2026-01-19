import pytest
from fastapi import HTTPException
from app.core.ratelimit import CostRateLimiter

def test_cost_rate_limiter_basic():
    limiter = CostRateLimiter(max_cost=0.05)
    
    # First request - OK
    limiter.check_and_inc("session1", 0.02)
    
    # Second request - OK
    limiter.check_and_inc("session1", 0.02)
    
    # Third request - Should fail because 0.02+0.02+0.02 = 0.06 > 0.05
    with pytest.raises(HTTPException) as exc:
        limiter.check_and_inc("session1", 0.02)
    assert exc.value.status_code == 429

def test_cost_rate_limiter_window():
    # Very short 1s window
    limiter = CostRateLimiter(window_seconds=1, max_cost=0.01)
    
    limiter.check_and_inc("session2", 0.01)
    
    with pytest.raises(HTTPException):
        limiter.check_and_inc("session2", 0.01)
        
    import time
    time.sleep(1.1)
    
    # Should work now
    limiter.check_and_inc("session2", 0.01)
