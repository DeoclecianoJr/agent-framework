"""Cost monitoring and alerting system.

Provides threshold monitoring and cost alerts for LLM usage.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.models import Message, Session

logger = logging.getLogger(__name__)


class CostAlert:
    """Represents a cost threshold alert."""
    
    def __init__(self, threshold_type: str, threshold_value: float, current_value: float, 
                 agent_id: Optional[str] = None, session_id: Optional[str] = None):
        self.threshold_type = threshold_type  # "daily", "monthly", "session"
        self.threshold_value = threshold_value
        self.current_value = current_value
        self.agent_id = agent_id
        self.session_id = session_id
        self.timestamp = datetime.now(timezone.utc)


class CostMonitor:
    """Monitors LLM usage costs and triggers alerts when thresholds are exceeded."""
    
    def __init__(self, db: Session):
        self.db = db
        self.daily_threshold = 10.0  # $10 per day default
        self.monthly_threshold = 100.0  # $100 per month default
        self.session_threshold = 5.0  # $5 per session default
        self.agent_daily_threshold = 5.0  # $5 per agent per day default
    
    def configure_thresholds(self, daily: float = None, monthly: float = None, 
                           session: float = None, agent_daily: float = None):
        """Configure cost thresholds."""
        if daily is not None:
            self.daily_threshold = daily
        if monthly is not None:
            self.monthly_threshold = monthly
        if session is not None:
            self.session_threshold = session
        if agent_daily is not None:
            self.agent_daily_threshold = agent_daily
    
    def check_cost_thresholds(self, session_id: str, agent_id: str, 
                            message_cost: float) -> List[CostAlert]:
        """Check if any cost thresholds are exceeded and return alerts."""
        alerts = []
        
        try:
            # Check session threshold
            session_cost = self._get_session_cost(session_id)
            if session_cost > self.session_threshold:
                alerts.append(CostAlert(
                    "session", self.session_threshold, session_cost, 
                    agent_id=agent_id, session_id=session_id
                ))
            
            # Check daily threshold (global)
            daily_cost = self._get_daily_cost()
            if daily_cost > self.daily_threshold:
                alerts.append(CostAlert(
                    "daily", self.daily_threshold, daily_cost
                ))
            
            # Check agent daily threshold
            agent_daily_cost = self._get_agent_daily_cost(agent_id)
            if agent_daily_cost > self.agent_daily_threshold:
                alerts.append(CostAlert(
                    "agent_daily", self.agent_daily_threshold, agent_daily_cost,
                    agent_id=agent_id
                ))
            
            # Check monthly threshold
            monthly_cost = self._get_monthly_cost()
            if monthly_cost > self.monthly_threshold:
                alerts.append(CostAlert(
                    "monthly", self.monthly_threshold, monthly_cost
                ))
                
        except Exception as e:
            logger.error(f"Error checking cost thresholds: {e}")
        
        return alerts
    
    def _get_session_cost(self, session_id: str) -> float:
        """Get total cost for a specific session from attrs."""
        messages = self.db.query(Message).filter(
            Message.session_id == session_id
        ).all()
        return sum(msg.attrs.get("usage", {}).get("cost", 0) for msg in messages)
    
    def _get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a specific day (default: today) from attrs."""
        if date is None:
            date = datetime.now(timezone.utc).date()
        
        start_time = datetime.combine(date, datetime.min.time())
        end_time = datetime.combine(date, datetime.max.time())
        
        messages = self.db.query(Message).filter(
            and_(
                Message.created_at >= start_time,
                Message.created_at <= end_time
            )
        ).all()
        return sum(msg.attrs.get("usage", {}).get("cost", 0) for msg in messages)
    
    def _get_agent_daily_cost(self, agent_id: str, date: Optional[datetime] = None) -> float:
        """Get total cost for a specific agent on a specific day from attrs."""
        if date is None:
            date = datetime.now(timezone.utc).date()
        
        start_time = datetime.combine(date, datetime.min.time())
        end_time = datetime.combine(date, datetime.max.time())
        
        # Join with Session to get agent_id
        messages = self.db.query(Message).join(
            Session, Message.session_id == Session.id
        ).filter(
            and_(
                Session.agent_id == agent_id,
                Message.created_at >= start_time,
                Message.created_at <= end_time
            )
        ).all()
        return sum(msg.attrs.get("usage", {}).get("cost", 0) for msg in messages)
    
    def _get_monthly_cost(self, year: int = None, month: int = None) -> float:
        """Get total cost for a specific month (default: current month) from attrs."""
        now = datetime.now(timezone.utc)
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        # First day of the month
        start_time = datetime(year, month, 1)
        
        # First day of next month
        if month == 12:
            end_time = datetime(year + 1, 1, 1)
        else:
            end_time = datetime(year, month + 1, 1)
        
        messages = self.db.query(Message).filter(
            and_(
                Message.created_at >= start_time,
                Message.created_at < end_time
            )
        ).all()
        return sum(msg.attrs.get("usage", {}).get("cost", 0) for msg in messages)
    
    def get_cost_summary(self, agent_id: str = None) -> Dict:
        """Get comprehensive cost summary."""
        try:
            today = datetime.now(timezone.utc).date()
            
            summary = {
                "daily_cost": self._get_daily_cost(today),
                "monthly_cost": self._get_monthly_cost(),
                "thresholds": {
                    "daily": self.daily_threshold,
                    "monthly": self.monthly_threshold,
                    "session": self.session_threshold,
                    "agent_daily": self.agent_daily_threshold
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if agent_id:
                summary["agent_daily_cost"] = self._get_agent_daily_cost(agent_id)
            
            # Add threshold status
            summary["status"] = {
                "daily_exceeded": summary["daily_cost"] > self.daily_threshold,
                "monthly_exceeded": summary["monthly_cost"] > self.monthly_threshold
            }
            
            if agent_id:
                summary["status"]["agent_daily_exceeded"] = summary["agent_daily_cost"] > self.agent_daily_threshold
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return {"error": str(e)}


class CostReporter:
    """Generates cost reports and historical analysis."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_daily_report(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get daily cost breakdown for a date range."""
        try:
            reports = []
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            while current_date <= end_date_only:
                day_start = datetime.combine(current_date, datetime.min.time())
                day_end = datetime.combine(current_date, datetime.max.time())
                
                # Get daily totals from attrs JSON field
                daily_messages = self.db.query(Message).filter(
                    and_(
                        Message.created_at >= day_start,
                        Message.created_at <= day_end
                    )
                ).all()
                
                total_cost = sum(msg.attrs.get("usage", {}).get("cost", 0) for msg in daily_messages)
                message_count = len(daily_messages)
                total_tokens = sum(msg.attrs.get("usage", {}).get("total_tokens", 0) for msg in daily_messages)
                
                # Get per-agent breakdown from attrs
                agent_sessions = self.db.query(
                    Session.agent_id,
                    Session.id
                ).filter(
                    Session.id.in_(
                        [msg.session_id for msg in daily_messages]
                    )
                ).all()
                
                agent_breakdown = {}
                for agent_id, session_id in agent_sessions:
                    session_messages = [m for m in daily_messages if m.session_id == session_id]
                    if agent_id not in agent_breakdown:
                        agent_breakdown[agent_id] = {"cost": 0, "count": 0}
                    agent_breakdown[agent_id]["cost"] += sum(m.attrs.get("usage", {}).get("cost", 0) for m in session_messages)
                    agent_breakdown[agent_id]["count"] += len(session_messages)
                
                # Get per-model breakdown from attrs
                model_breakdown = {}
                for msg in daily_messages:
                    model = msg.attrs.get("usage", {}).get("model")
                    if model:
                        if model not in model_breakdown:
                            model_breakdown[model] = {"cost": 0, "count": 0}
                        model_breakdown[model]["cost"] += msg.attrs.get("usage", {}).get("cost", 0)
                        model_breakdown[model]["count"] += 1
                
                report = {
                    "date": current_date.isoformat(),
                    "total_cost": float(total_cost),
                    "total_messages": int(message_count),
                    "total_tokens": int(total_tokens),
                    "agents": [
                        {
                            "agent_id": agent_id,
                            "cost": float(data["cost"]),
                            "messages": int(data["count"])
                        }
                        for agent_id, data in agent_breakdown.items()
                    ],
                    "models": [
                        {
                            "model": model,
                            "cost": float(data["cost"]),
                            "messages": int(data["count"])
                        }
                        for model, data in model_breakdown.items()
                    ]
                }
                reports.append(report)
                
                # Move to next day
                current_date += timedelta(days=1)
            
            return reports
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return []
    
    def get_top_cost_sessions(self, limit: int = 10, days: int = 7) -> List[Dict]:
        """Get sessions with highest costs in the last N days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get all messages within time period with session info
            results = self.db.query(
                Message.session_id,
                Session.agent_id,
                func.count(Message.id).label('message_count'),
                func.max(Message.created_at).label('last_activity')
            ).join(
                Session, Message.session_id == Session.id
            ).filter(
                Message.created_at >= cutoff_date
            ).group_by(
                Message.session_id, Session.agent_id
            ).all()
            
            # Calculate cost from attrs for each session
            session_costs = []
            for row in results:
                messages = self.db.query(Message).filter(
                    Message.session_id == row.session_id
                ).all()
                session_cost = sum(msg.attrs.get("usage", {}).get("cost", 0) for msg in messages)
                session_costs.append({
                    "session_id": row.session_id,
                    "agent_id": row.agent_id,
                    "cost": session_cost,
                    "message_count": row.message_count,
                    "last_activity": row.last_activity
                })
            
            # Sort by cost descending and limit
            session_costs.sort(key=lambda x: x["cost"], reverse=True)
            session_costs = session_costs[:limit]
            
            return [
                {
                    "session_id": item["session_id"],
                    "agent_id": item["agent_id"],
                    "total_cost": float(item["cost"]),
                    "message_count": int(item["message_count"]),
                    "last_activity": item["last_activity"].isoformat()
                }
                for item in session_costs
            ]
            
        except Exception as e:
            logger.error(f"Error getting top cost sessions: {e}")
            return []