"""Cost reporting and analysis endpoints.

Provides detailed cost reports and historical analysis.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.cost_monitoring import CostMonitor, CostReporter
from app.core.logging import get_logger

router = APIRouter(prefix="/reports", tags=["reports"])
logger = get_logger(__name__)


@router.get("/cost-summary")
def get_cost_summary(
    agent_id: Optional[str] = Query(None, description="Filter by specific agent"),
    db: Session = Depends(get_db)
):
    """Get current cost summary with threshold status."""
    try:
        cost_monitor = CostMonitor(db)
        summary = cost_monitor.get_cost_summary(agent_id)
        return summary
    except Exception as e:
        logger.error(f"Error getting cost summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cost summary")


@router.get("/daily-costs")
def get_daily_cost_report(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Get daily cost breakdown for a date range."""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        if (end_dt - start_dt).days > 31:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 31 days")
        
        cost_reporter = CostReporter(db)
        reports = cost_reporter.get_daily_report(start_dt, end_dt)
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "daily_reports": reports,
            "summary": {
                "total_days": len(reports),
                "total_cost": sum(r["total_cost"] for r in reports),
                "total_messages": sum(r["total_messages"] for r in reports),
                "average_daily_cost": sum(r["total_cost"] for r in reports) / len(reports) if reports else 0
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error getting daily cost report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate daily cost report")


@router.get("/top-cost-sessions")
def get_top_cost_sessions(
    limit: int = Query(10, ge=1, le=50, description="Number of sessions to return"),
    days: int = Query(7, ge=1, le=30, description="Look back N days"),
    db: Session = Depends(get_db)
):
    """Get sessions with highest costs in the last N days."""
    try:
        cost_reporter = CostReporter(db)
        sessions = cost_reporter.get_top_cost_sessions(limit, days)
        
        return {
            "limit": limit,
            "days_lookback": days,
            "sessions": sessions,
            "summary": {
                "total_sessions": len(sessions),
                "highest_cost": sessions[0]["total_cost"] if sessions else 0,
                "total_cost": sum(s["total_cost"] for s in sessions),
                "average_cost": sum(s["total_cost"] for s in sessions) / len(sessions) if sessions else 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting top cost sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top cost sessions")


@router.post("/cost-thresholds")
def configure_cost_thresholds(
    daily_threshold: Optional[float] = None,
    monthly_threshold: Optional[float] = None,
    session_threshold: Optional[float] = None,
    agent_daily_threshold: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Configure cost monitoring thresholds."""
    try:
        cost_monitor = CostMonitor(db)
        cost_monitor.configure_thresholds(
            daily=daily_threshold,
            monthly=monthly_threshold,
            session=session_threshold,
            agent_daily=agent_daily_threshold
        )
        
        return {
            "message": "Cost thresholds updated successfully",
            "thresholds": {
                "daily": cost_monitor.daily_threshold,
                "monthly": cost_monitor.monthly_threshold,
                "session": cost_monitor.session_threshold,
                "agent_daily": cost_monitor.agent_daily_threshold
            }
        }
    except Exception as e:
        logger.error(f"Error configuring cost thresholds: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure cost thresholds")


@router.get("/cost-trends")
def get_cost_trends(
    days: int = Query(30, ge=7, le=90, description="Number of days for trend analysis"),
    db: Session = Depends(get_db)
):
    """Get cost trend analysis over the last N days."""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        cost_reporter = CostReporter(db)
        daily_reports = cost_reporter.get_daily_report(start_date, end_date)
        
        # Calculate trends
        if len(daily_reports) >= 2:
            recent_avg = sum(r["total_cost"] for r in daily_reports[-7:]) / min(7, len(daily_reports))
            older_avg = sum(r["total_cost"] for r in daily_reports[:-7]) / max(1, len(daily_reports) - 7)
            trend_percentage = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        else:
            recent_avg = daily_reports[0]["total_cost"] if daily_reports else 0
            older_avg = 0
            trend_percentage = 0
        
        return {
            "period_days": days,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "daily_data": daily_reports,
            "trend_analysis": {
                "recent_7day_average": round(recent_avg, 4),
                "older_period_average": round(older_avg, 4),
                "trend_percentage": round(trend_percentage, 2),
                "trend_direction": "increasing" if trend_percentage > 5 else "decreasing" if trend_percentage < -5 else "stable"
            },
            "total_cost": sum(r["total_cost"] for r in daily_reports),
            "peak_day": max(daily_reports, key=lambda x: x["total_cost"]) if daily_reports else None
        }
    except Exception as e:
        logger.error(f"Error getting cost trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate cost trends")