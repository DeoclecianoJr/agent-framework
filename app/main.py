from fastapi import FastAPI, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.middleware import APIKeyMiddleware
from app.middleware_trace import TraceIDMiddleware
from app.middleware_metrics import MetricsMiddleware
from app.core.logging import setup_logging, get_logger

from app.core.models import Base
from app.core.dependencies import init_db
from app.core.config import api_settings

# Import API routers
from app.api import health_router, admin_router, chat_router

# Setup logging
setup_logging(level=api_settings.log_level)
logger = get_logger(__name__)

# Security scheme for Swagger UI
api_key_header = APIKeyHeader(name=api_settings.api_key_header_name, auto_error=False)

app = FastAPI(
    title="AI Framework",
    version="0.1.0",
    debug=api_settings.debug,
)

# Override OpenAPI to ensure security scheme is present
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "name": api_settings.api_key_header_name,
            "in": "header",
        }
    }
    # Apply security to all routes
    openapi_schema["security"] = [{"APIKeyHeader": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

from fastapi.openapi.utils import get_openapi
app.openapi = custom_openapi

# Add middlewares (order matters: TraceID first, then API Key)
app.add_middleware(TraceIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(APIKeyMiddleware)



# Database setup
engine = create_engine(
    api_settings.database_url,
    connect_args={"check_same_thread": False} if api_settings.database_url.startswith("sqlite") else {}
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize dependencies
init_db(SessionLocal)


# Register API routers
app.include_router(health_router)
app.include_router(admin_router)
app.include_router(chat_router)
