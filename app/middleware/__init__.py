"""
Middleware package for AI Framework.

Contains all middleware components for the FastAPI application:
- auth: API key authentication middleware
- trace: Request tracing middleware for observability
- metrics: Application metrics collection middleware
"""

from .auth import APIKeyMiddleware
from .trace import TraceIDMiddleware
from .metrics import MetricsMiddleware

__all__ = [
    "APIKeyMiddleware",
    "TraceIDMiddleware", 
    "MetricsMiddleware",
]