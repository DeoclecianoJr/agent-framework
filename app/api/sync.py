"""
Sync API Endpoints.

REST API for controlling document synchronization.

Story 7.5: Document Sync Scheduler
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.dependencies import get_db
from ai_framework.core.sync import DocumentSyncManager, SyncScheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

# Global scheduler instance (initialized in main.py)
_scheduler: Optional[SyncScheduler] = None


def get_scheduler() -> SyncScheduler:
    """Get global scheduler instance."""
    if _scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    return _scheduler


def set_scheduler(scheduler: SyncScheduler):
    """Set global scheduler instance."""
    global _scheduler
    _scheduler = scheduler


# ==================== Request/Response Models ====================

class SyncSourceRequest(BaseModel):
    """Request to sync a source."""
    source_id: str = Field(..., description="Knowledge source ID")
    force_full_sync: bool = Field(False, description="Force full sync ignoring last_sync_at")
    enable_embeddings: bool = Field(True, description="Generate embeddings automatically (default: True)")
    embedding_provider: str = Field('local', description="Embedding provider (local, openai, gemini)")
    embedding_model: Optional[str] = Field(None, description="Embedding model name")


class ScheduleSyncRequest(BaseModel):
    """Request to schedule periodic sync."""
    source_id: str = Field(..., description="Knowledge source ID")
    interval_minutes: Optional[int] = Field(None, description="Sync interval in minutes")
    cron_expression: Optional[str] = Field(None, description="Cron expression (e.g., '0 2 * * *')")
    force_full_sync: bool = Field(False, description="Force full sync on each run")


class SyncResultResponse(BaseModel):
    """Sync operation result."""
    source_id: str
    started_at: Optional[str]
    completed_at: Optional[str]
    status: str
    files_found: int
    files_added: int
    files_updated: int
    files_deleted: int
    errors: list
    duration_seconds: Optional[float]


class ScheduledJobResponse(BaseModel):
    """Scheduled job information."""
    id: str
    name: str
    next_run_time: Optional[str]
    trigger: str


# ==================== Endpoints ====================

@router.post("/sources/sync", response_model=SyncResultResponse)
def sync_source(
    request: SyncSourceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Manually trigger sync for a specific knowledge source.
    
    This endpoint triggers an immediate sync and returns the result.
    For background sync, use the schedule endpoint.
    """
    try:
        manager = DocumentSyncManager(
            db,
            enable_embeddings=request.enable_embeddings,
            embedding_provider=request.embedding_provider,
            embedding_model=request.embedding_model
        )
        result = manager.sync_source(
            source_id=request.source_id,
            force_full_sync=request.force_full_sync
        )
        
        return SyncResultResponse(**result.to_dict())
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/sync-all")
def sync_all_sources(
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Sync all knowledge sources.
    
    Args:
        agent_id: Optional filter by agent ID
    """
    try:
        manager = DocumentSyncManager(db)
        results = manager.sync_all_sources(agent_id)
        
        return {
            "total_sources": len(results),
            "results": [SyncResultResponse(**r.to_dict()) for r in results]
        }
        
    except Exception as e:
        logger.error(f"Sync all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule", response_model=dict)
def schedule_sync(
    request: ScheduleSyncRequest,
    scheduler: SyncScheduler = Depends(get_scheduler)
):
    """
    Schedule periodic sync for a knowledge source.
    
    Either interval_minutes or cron_expression must be provided.
    """
    try:
        job_id = scheduler.schedule_source_sync(
            source_id=request.source_id,
            interval_minutes=request.interval_minutes,
            cron_expression=request.cron_expression,
            force_full_sync=request.force_full_sync
        )
        
        return {
            "message": "Sync scheduled successfully",
            "job_id": job_id,
            "source_id": request.source_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Schedule sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedule/{source_id}")
def unschedule_sync(
    source_id: str,
    scheduler: SyncScheduler = Depends(get_scheduler)
):
    """
    Remove scheduled sync for a source.
    """
    try:
        scheduler.unschedule_source_sync(source_id)
        return {"message": f"Sync unscheduled for source {source_id}"}
        
    except Exception as e:
        logger.error(f"Unschedule sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=list[ScheduledJobResponse])
def get_scheduled_jobs(
    scheduler: SyncScheduler = Depends(get_scheduler)
):
    """
    Get list of all scheduled sync jobs.
    """
    try:
        jobs = scheduler.get_scheduled_jobs()
        return [ScheduledJobResponse(**job) for job in jobs]
        
    except Exception as e:
        logger.error(f"Get jobs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def get_scheduler_status(
    scheduler: SyncScheduler = Depends(get_scheduler)
):
    """
    Get scheduler status.
    """
    return {
        "running": scheduler.is_running(),
        "total_jobs": len(scheduler.get_scheduled_jobs())
    }


@router.post("/scheduler/start")
def start_scheduler(
    scheduler: SyncScheduler = Depends(get_scheduler)
):
    """
    Start the sync scheduler.
    """
    try:
        scheduler.start()
        return {"message": "Scheduler started"}
        
    except Exception as e:
        logger.error(f"Start scheduler failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
def stop_scheduler(
    scheduler: SyncScheduler = Depends(get_scheduler)
):
    """
    Stop the sync scheduler.
    """
    try:
        scheduler.stop()
        return {"message": "Scheduler stopped"}
        
    except Exception as e:
        logger.error(f"Stop scheduler failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
