from sqlalchemy.orm import Session
from app.core.models import AuditLog
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def log_audit_event(
    db: Session,
    event_type: str,
    event_data: Dict[str, Any],
    actor: Optional[str] = None,
    commit: bool = True
) -> AuditLog:
    """
    Log a security-critical event to the audit log.
    
    Args:
        db: Database session
        event_type: Type of event (e.g., "create_api_key")
        event_data: JSON-serializable details
        actor: Identifier of the actor (e.g., "admin", "system", IP)
        commit: Whether to commit the transaction immediately
        
    Returns:
        Created AuditLog entry
    """
    try:
        entry = AuditLog(
            event_type=event_type,
            event_data=event_data,
            actor=actor
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        return entry
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        # Don't crash the application if logging fails, but log to stderr
        return None
