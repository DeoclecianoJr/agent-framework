"""
Document Sync Scheduler.

Provides background scheduling for automatic document synchronization
using APScheduler.

Story 7.5: Document Sync Scheduler
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from sqlalchemy.orm import Session

from .manager import DocumentSyncManager, SyncResult

logger = logging.getLogger(__name__)


class SyncScheduler:
    """
    Background scheduler for document synchronization.
    
    Features:
    - Interval-based scheduling (e.g., every 5 minutes)
    - Cron-based scheduling (e.g., daily at 2am)
    - Per-source scheduling
    - Job monitoring and control
    
    Usage:
        scheduler = SyncScheduler(db_session_factory)
        
        # Schedule source sync every 5 minutes
        scheduler.schedule_source_sync(source_id, interval_minutes=5)
        
        # Start scheduler
        scheduler.start()
        
        # Stop scheduler
        scheduler.stop()
    """
    
    def __init__(
        self,
        db_session_factory,
        timezone: str = 'UTC'
    ):
        """
        Initialize sync scheduler.
        
        Args:
            db_session_factory: Factory function to create DB sessions
            timezone: Timezone for cron jobs
        """
        self.db_session_factory = db_session_factory
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self.sync_jobs: Dict[str, Job] = {}  # source_id -> Job
        self._running = False
    
    def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Sync scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Sync scheduler stopped")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    def schedule_source_sync(
        self,
        source_id: str,
        interval_minutes: Optional[int] = None,
        cron_expression: Optional[str] = None,
        force_full_sync: bool = False
    ) -> str:
        """
        Schedule periodic sync for a knowledge source.
        
        Args:
            source_id: KnowledgeSource ID
            interval_minutes: Sync interval in minutes (e.g., 5 for every 5 minutes)
            cron_expression: Cron expression (e.g., "0 2 * * *" for daily at 2am)
            force_full_sync: Force full sync on each run
            
        Returns:
            str: Job ID
            
        Raises:
            ValueError: If neither interval nor cron provided
        """
        if not interval_minutes and not cron_expression:
            raise ValueError("Must provide either interval_minutes or cron_expression")
        
        # Remove existing job if any
        if source_id in self.sync_jobs:
            self.unschedule_source_sync(source_id)
        
        # Create trigger
        if interval_minutes:
            trigger = IntervalTrigger(minutes=interval_minutes)
            schedule_desc = f"every {interval_minutes} minutes"
        else:
            trigger = CronTrigger.from_crontab(cron_expression)
            schedule_desc = f"cron: {cron_expression}"
        
        # Schedule job
        job = self.scheduler.add_job(
            func=self._sync_source_job,
            trigger=trigger,
            args=[source_id, force_full_sync],
            id=f"sync_{source_id}",
            name=f"Sync source {source_id}",
            replace_existing=True,
            max_instances=1  # Prevent concurrent syncs of same source
        )
        
        self.sync_jobs[source_id] = job
        
        logger.info(f"Scheduled sync for source {source_id}: {schedule_desc}")
        return job.id
    
    def schedule_all_sources_sync(
        self,
        interval_minutes: int = 60,
        agent_id: Optional[str] = None
    ) -> str:
        """
        Schedule periodic sync for all knowledge sources.
        
        Args:
            interval_minutes: Sync interval in minutes
            agent_id: Optional filter by agent ID
            
        Returns:
            str: Job ID
        """
        trigger = IntervalTrigger(minutes=interval_minutes)
        
        job = self.scheduler.add_job(
            func=self._sync_all_sources_job,
            trigger=trigger,
            args=[agent_id],
            id=f"sync_all_{agent_id or 'global'}",
            name=f"Sync all sources (agent: {agent_id or 'all'})",
            replace_existing=True
        )
        
        logger.info(
            f"Scheduled sync for all sources (agent: {agent_id or 'all'}): "
            f"every {interval_minutes} minutes"
        )
        return job.id
    
    def unschedule_source_sync(self, source_id: str):
        """
        Remove scheduled sync for a source.
        
        Args:
            source_id: KnowledgeSource ID
        """
        if source_id in self.sync_jobs:
            job = self.sync_jobs[source_id]
            job.remove()
            del self.sync_jobs[source_id]
            logger.info(f"Unscheduled sync for source {source_id}")
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """
        Get list of scheduled jobs.
        
        Returns:
            List[Dict]: Job information
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def trigger_source_sync(
        self,
        source_id: str,
        force_full_sync: bool = False
    ) -> SyncResult:
        """
        Manually trigger sync for a source (run immediately).
        
        Args:
            source_id: KnowledgeSource ID
            force_full_sync: Force full sync
            
        Returns:
            SyncResult: Sync result
        """
        logger.info(f"Manual sync triggered for source {source_id}")
        return self._sync_source_job(source_id, force_full_sync)
    
    def _sync_source_job(
        self,
        source_id: str,
        force_full_sync: bool = False
    ) -> SyncResult:
        """
        Job function to sync a source.
        
        Args:
            source_id: KnowledgeSource ID
            force_full_sync: Force full sync
            
        Returns:
            SyncResult: Sync result
        """
        db = self.db_session_factory()
        try:
            manager = DocumentSyncManager(db)
            result = manager.sync_source(source_id, force_full_sync)
            
            if result.status == "completed":
                logger.info(
                    f"Scheduled sync completed for {source_id}: "
                    f"+{result.files_added} ~{result.files_updated} -{result.files_deleted}"
                )
            else:
                logger.error(
                    f"Scheduled sync failed for {source_id}: {result.errors}"
                )
            
            return result
        finally:
            db.close()
    
    def _sync_all_sources_job(self, agent_id: Optional[str] = None):
        """
        Job function to sync all sources.
        
        Args:
            agent_id: Optional filter by agent ID
        """
        db = self.db_session_factory()
        try:
            manager = DocumentSyncManager(db)
            results = manager.sync_all_sources(agent_id)
            
            total_added = sum(r.files_added for r in results)
            total_updated = sum(r.files_updated for r in results)
            total_deleted = sum(r.files_deleted for r in results)
            
            logger.info(
                f"Scheduled sync all completed: {len(results)} sources, "
                f"+{total_added} ~{total_updated} -{total_deleted}"
            )
        finally:
            db.close()
