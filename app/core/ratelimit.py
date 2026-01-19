"""Rate limiting utilities based on costs and token usage."""
import time
from typing import Dict, Optional
from fastapi import HTTPException, status

class CostRateLimiter:
    """Rate limiter that tracks accumulated cost per session/user."""

    def __init__(self, window_seconds: int = 3600, max_cost: float = 1.0):
        self.window_seconds = window_seconds
        self.max_cost = max_cost
        # session_id -> [(timestamp, cost)]
        self.history: Dict[str, list] = {}

    def _cleanup(self, session_id: str, now: float):
        """Remove entries outside the current window."""
        if session_id not in self.history:
            return
        
        self.history[session_id] = [
            (ts, cost) for ts, cost in self.history[session_id]
            if now - ts < self.window_seconds
        ]

    def check_and_inc(self, session_id: str, estimated_cost: float = 0.0):
        """Check if request is allowed and increment cost.
        
        Raises:
            HTTPException 429 if limit exceeded.
        """
        now = time.time()
        self._cleanup(session_id, now)
        
        current_total = sum(cost for ts, cost in self.history.get(session_id, []))
        
        if current_total + estimated_cost > self.max_cost:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded by cost. Max {self.max_cost} per {self.window_seconds}s. Current: {current_total:.4f}"
            )
            
        if session_id not in self.history:
            self.history[session_id] = []
            
        self.history[session_id].append((now, estimated_cost))

# Global instance for the app
cost_limiter = CostRateLimiter(max_cost=10.0) # $10 per hour default
