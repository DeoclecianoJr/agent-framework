"""Health check and monitoring endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.dependencies import get_db
from app.core.metrics import get_metrics_report

logger = get_logger(__name__)


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint reporting DB and LLM status (no auth required).
    
    Returns:
        {
            "db": "ok" | "error",
            "llm": "ok"  // Mocked for now
        }
    """
    db_status = "ok"
    llm_status = "ok"  # Mock for now

    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        db_status = "ok"
        logger.info("Health check: database OK")
    except Exception as e:
        db_status = "error"
        logger.error(f"Health check: database error - {str(e)}")

    return {
        "db": db_status,
        "llm": llm_status
    }


@router.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics_report()

