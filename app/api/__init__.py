"""API package initialization.

Exports all API routers for easy registration.
"""
from app.api.health import router as health_router
from app.api.admin import router as admin_router
from app.api.chat import router as chat_router

__all__ = [
    "health_router",
    "admin_router",
    "chat_router",
]
