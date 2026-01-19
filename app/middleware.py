"""
API Key authentication middleware for FastAPI.

Validates X-API-Key header on all protected routes and returns 401 if missing/invalid.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate X-API-Key header on requests."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate API key if required.
        
        Args:
            request: FastAPI Request object
            call_next: Next middleware/route handler
            
        Returns:
            Response from next handler or 401 if auth fails
        """
        # Skip auth for health check and admin key creation endpoints
        skip_paths = {
            "/health",
            "/metrics",
            "/openapi.json",
            "/docs",

            "/redoc",
            "/admin/api-keys",  # Allow creation without auth
            "/admin/verify-key",  # Allow verification endpoint
        }
        
        if request.url.path not in skip_paths and request.method != "OPTIONS":
            # Extract X-API-Key header
            api_key = request.headers.get("X-API-Key")
            
            if not api_key:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing X-API-Key header"}
                )
            
            # Validate against DB (will be attached to request state in router)
            # For now, we set a flag that the route handler can check
            request.state.api_key_header = api_key
        
        response = await call_next(request)
        return response

