"""Health check and monitoring endpoints."""
from datetime import datetime, timezone
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
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    from app.core.metrics import registry

    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@router.get("/prometheus")
def prometheus_metrics():
    """Prometheus metrics endpoint for scraping."""
    return get_metrics_report()


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    """Advanced analytics endpoint with detailed performance metrics."""
    from sqlalchemy import func, extract, desc
    from app.core.models import Message, Session as SessionModel
    from datetime import datetime, timedelta
    
    try:
        # Performance metrics by hour (last 24h)
        yesterday = datetime.utcnow() - timedelta(days=1)
        hourly_stats = db.query(
            extract('hour', Message.created_at).label('hour'),
            func.count(Message.id).label('message_count'),
            func.sum(Message.tokens_used).label('total_tokens'),
            func.sum(Message.cost).label('total_cost'),
            func.avg(Message.tokens_used).label('avg_tokens_per_message')
        ).filter(
            Message.created_at >= yesterday,
            Message.role == 'assistant'
        ).group_by(extract('hour', Message.created_at)).all()
        
        # Top sessions by activity
        top_sessions = db.query(
            SessionModel.id,
            SessionModel.agent_id,
            func.count(Message.id).label('message_count'),
            func.sum(Message.cost).label('session_cost'),
            func.max(Message.created_at).label('last_activity')
        ).join(
            Message, SessionModel.id == Message.session_id
        ).group_by(
            SessionModel.id, SessionModel.agent_id
        ).order_by(desc(func.count(Message.id))).limit(10).all()
        
        # Cost efficiency by model
        model_efficiency = db.query(
            Message.model,
            func.count(Message.id).label('message_count'),
            func.avg(Message.cost).label('avg_cost_per_message'),
            func.avg(Message.tokens_used).label('avg_tokens_per_message'),
            func.sum(Message.cost).label('total_cost'),
            func.sum(Message.tokens_used).label('total_tokens')
        ).filter(
            Message.model.isnot(None),
            Message.role == 'assistant'
        ).group_by(Message.model).all()
        
        return {
            "performance": {
                "hourly_activity": [
                    {
                        "hour": int(hour),
                        "message_count": count,
                        "total_tokens": tokens or 0,
                        "total_cost_usd": round(float(cost or 0), 4),
                        "avg_tokens_per_message": round(float(avg_tokens or 0), 2)
                    }
                    for hour, count, tokens, cost, avg_tokens in hourly_stats
                ],
                "peak_hour": max(hourly_stats, key=lambda x: x[1])[0] if hourly_stats else None
            },
            "sessions": {
                "most_active": [
                    {
                        "session_id": str(session_id),
                        "agent_id": agent_id,
                        "message_count": count,
                        "session_cost_usd": round(float(cost or 0), 4),
                        "last_activity": last_activity.isoformat() if last_activity else None
                    }
                    for session_id, agent_id, count, cost, last_activity in top_sessions
                ]
            },
            "model_efficiency": [
                {
                    "model": model,
                    "message_count": count,
                    "avg_cost_per_message_usd": round(float(avg_cost or 0), 6),
                    "avg_tokens_per_message": round(float(avg_tokens or 0), 2),
                    "total_cost_usd": round(float(total_cost or 0), 4),
                    "total_tokens": total_tokens or 0,
                    "cost_per_1k_tokens": round(float((avg_cost or 0) * 1000 / (avg_tokens or 1)), 6)
                }
                for model, count, avg_cost, avg_tokens, total_cost, total_tokens in model_efficiency
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating analytics: {str(e)}")
        return {
            "error": "Failed to generate analytics",
            "performance": {"hourly_activity": [], "peak_hour": None},
            "sessions": {"most_active": []},
            "model_efficiency": [],
            "timestamp": datetime.utcnow().isoformat()
        }

