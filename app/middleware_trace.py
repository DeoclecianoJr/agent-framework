"""Trace ID middleware for request tracking and correlation."""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import set_trace_id, get_trace_id


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Middleware that generates and propagates trace_id for each request."""

    async def dispatch(self, request: Request, call_next):
        """Generate trace_id and add to request context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with trace_id header
        """
        # Generate trace_id from header or create new one
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        
        # Set trace_id in context for logging
        set_trace_id(trace_id)

        # Process request
        response = await call_next(request)
        
        # Add trace_id to response headers for client tracking
        response.headers["X-Trace-ID"] = trace_id

        return response
