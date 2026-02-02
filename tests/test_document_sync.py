"""
Tests for Document Sync Manager and Scheduler (Story 7.5).

Tests:
- DocumentSyncManager operations
- Change detection (new, updated, deleted)
- SyncScheduler background jobs
- Sync API endpoints
- Error handling
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models import Base, KnowledgeSource, KnowledgeDocument, Agent
from ai_framework.core.sync import DocumentSyncManager, SyncResult, SyncScheduler
from ai_framework.core.storage import FileMetadata, StorageCredentials


# ==================== Fixtures ====================

@pytest.fixture
def sqlite_memory_db():
    """Create in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_agent(sqlite_memory_db):
    """Create test agent."""
    agent = Agent(
        id="test-agent-id",
        name="Test Agent",
        description="Test agent for sync tests"
    )
    sqlite_memory_db.add(agent)
    sqlite_memory_db.commit()
    return agent


@pytest.fixture
def test_source(sqlite_memory_db, test_agent):
    """Create test knowledge source."""
    credentials = StorageCredentials(
        access_token='test-token',
        refresh_token='refresh-token',
        token_expiry=datetime.utcnow() + timedelta(hours=1),
        scopes=['drive.readonly'],
        extra={'client_id': 'test-id', 'client_secret': 'test-secret'}
    )
    
    from ai_framework.core.storage import OAuthManager
    
    # Store credentials in config JSON field
    config_data = {
        'folder_id': 'root',
        'credentials': OAuthManager.serialize_credentials(credentials)
    }
    
    source = KnowledgeSource(
        id="test-source-id",
        agent_id=test_agent.id,
        source_type="google_drive",
        config=config_data,
        sync_status="pending"
    )
    sqlite_memory_db.add(source)
    sqlite_memory_db.commit()
    return source



@pytest.fixture
def mock_file_metadata():
    """Create mock file metadata."""
    return [
        FileMetadata(
            id='file1',
            name='document1.pdf',
            mime_type='application/pdf',
            size=1024,
            modified_at=datetime.utcnow(),
            created_at=datetime.utcnow() - timedelta(days=1),
            web_url='https://drive.google.com/file/d/file1',
            parent_id=None,
            is_folder=False,
            path='/document1.pdf',
            extra={}
        ),
        FileMetadata(
            id='file2',
            name='document2.docx',
            mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            size=2048,
            modified_at=datetime.utcnow(),
            created_at=datetime.utcnow() - timedelta(days=2),
            web_url='https://drive.google.com/file/d/file2',
            parent_id=None,
            is_folder=False,
            path='/document2.docx',
            extra={}
        )
    ]


# ==================== DocumentSyncManager Tests ====================

class TestDocumentSyncManager:
    """Test document sync manager."""
    
    @patch('ai_framework.core.sync.manager.StorageProviderFactory')
    def test_sync_source_new_files(self, mock_factory, sqlite_memory_db, test_source, mock_file_metadata):
        """Can sync new files from source."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.list_files.return_value = mock_file_metadata
        mock_factory.create_from_knowledge_source.return_value = mock_provider
        
        # Sync source
        manager = DocumentSyncManager(sqlite_memory_db)
        result = manager.sync_source(test_source.id)
        
        # Verify result
        assert result.status == "completed"
        assert result.files_found == 2
        assert result.files_added == 2
        assert result.files_updated == 0
        assert result.files_deleted == 0
        
        # Verify documents created
        # Query by agent_id and check attrs contains source_db_id
        docs = sqlite_memory_db.query(KnowledgeDocument).filter_by(agent_id=test_source.agent_id).all()
        docs = [d for d in docs if d.attrs.get('source_db_id') == test_source.id]
        assert len(docs) == 2
        # Note: source_id now contains the file ID from storage provider
        assert {doc.source_id for doc in docs} == {'file1', 'file2'}
    
    @patch('ai_framework.core.sync.manager.StorageProviderFactory')
    def test_sync_source_updated_files(self, mock_factory, sqlite_memory_db, test_source):
        """Can detect and update modified files."""
        # Create existing document
        old_modified = datetime.utcnow() - timedelta(hours=2)
        doc = KnowledgeDocument(
            agent_id=test_source.agent_id,
            source_id='file1',  # File ID from storage provider
            source_type='google_drive',
            file_name='old_name.pdf',
            content_chunk='',
            chunk_index=0,
            attrs={'source_db_id': test_source.id},
            updated_at=old_modified
        )
        sqlite_memory_db.add(doc)
        sqlite_memory_db.commit()
        
        # Mock provider with updated file
        new_modified = datetime.utcnow()
        mock_file = FileMetadata(
            id='file1',
            name='new_name.pdf',
            mime_type='application/pdf',
            size=1024,
            modified_at=new_modified,
            created_at=old_modified,
            web_url='https://drive.google.com/file/d/file1',
            parent_id=None,
            is_folder=False,
            path='/new_name.pdf',
            extra={}
        )
        
        mock_provider = Mock()
        mock_provider.list_files.return_value = [mock_file]
        mock_factory.create_from_knowledge_source.return_value = mock_provider
        
        # Sync source
        manager = DocumentSyncManager(sqlite_memory_db)
        result = manager.sync_source(test_source.id)
        
        # Verify result
        assert result.status == "completed"
        assert result.files_found == 1
        assert result.files_added == 0
        assert result.files_updated == 1
        assert result.files_deleted == 0
        
        # Verify document updated
        sqlite_memory_db.refresh(doc)
        assert doc.file_name == 'new_name.pdf'
    
    @patch('ai_framework.core.sync.manager.StorageProviderFactory')
    def test_sync_source_deleted_files(self, mock_factory, sqlite_memory_db, test_source):
        """Can detect and delete removed files."""
        # Create existing document
        doc = KnowledgeDocument(
            agent_id=test_source.agent_id,
            source_id='file1',  # File ID from storage provider
            source_type='google_drive',
            file_name='document.pdf',
            content_chunk='',
            chunk_index=0,
            attrs={'source_db_id': test_source.id}
        )
        sqlite_memory_db.add(doc)
        sqlite_memory_db.commit()
        
        # Mock provider with no files (file was deleted)
        mock_provider = Mock()
        mock_provider.list_files.return_value = []
        mock_factory.create_from_knowledge_source.return_value = mock_provider
        
        # Sync source
        manager = DocumentSyncManager(sqlite_memory_db)
        result = manager.sync_source(test_source.id)
        
        # Verify result
        assert result.status == "completed"
        assert result.files_found == 0
        assert result.files_added == 0
        assert result.files_updated == 0
        assert result.files_deleted == 1
        
        # Verify document deleted
        doc_count = sqlite_memory_db.query(KnowledgeDocument).filter_by(id=doc.id).count()
        assert doc_count == 0
    
    @patch('ai_framework.core.sync.manager.StorageProviderFactory')
    def test_sync_source_updates_last_sync_at(self, mock_factory, sqlite_memory_db, test_source):
        """Updates last_sync_at timestamp after successful sync."""
        mock_provider = Mock()
        mock_provider.list_files.return_value = []
        mock_factory.create_from_knowledge_source.return_value = mock_provider
        
        # Verify initial state
        assert test_source.last_sync_at is None
        
        # Sync source
        manager = DocumentSyncManager(sqlite_memory_db)
        result = manager.sync_source(test_source.id)
        
        # Verify last_sync_at updated
        sqlite_memory_db.refresh(test_source)
        assert test_source.last_sync_at is not None
        assert test_source.sync_status == "completed"
    
    def test_sync_source_not_found(self, sqlite_memory_db):
        """Returns error for non-existent source."""
        manager = DocumentSyncManager(sqlite_memory_db)
        result = manager.sync_source("non-existent-id")
        
        assert result.status == "failed"
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()
    
    @patch('ai_framework.core.sync.manager.StorageProviderFactory')
    def test_sync_all_sources(self, mock_factory, sqlite_memory_db, test_source):
        """Can sync all sources."""
        mock_provider = Mock()
        mock_provider.list_files.return_value = []
        mock_factory.create_from_knowledge_source.return_value = mock_provider
        
        manager = DocumentSyncManager(sqlite_memory_db)
        results = manager.sync_all_sources()
        
        assert len(results) == 1
        assert results[0].source_id == test_source.id


# ==================== SyncScheduler Tests ====================

class TestSyncScheduler:
    """Test sync scheduler."""
    
    def test_scheduler_start_stop(self):
        """Can start and stop scheduler."""
        scheduler = SyncScheduler(db_session_factory=Mock())
        
        assert not scheduler.is_running()
        
        scheduler.start()
        assert scheduler.is_running()
        
        scheduler.stop()
        assert not scheduler.is_running()
    
    def test_schedule_source_sync_interval(self):
        """Can schedule source sync with interval."""
        scheduler = SyncScheduler(db_session_factory=Mock())
        scheduler.start()
        
        job_id = scheduler.schedule_source_sync(
            source_id='test-source',
            interval_minutes=5
        )
        
        assert job_id is not None
        assert 'test-source' in scheduler.sync_jobs
        
        scheduler.stop()
    
    def test_schedule_source_sync_cron(self):
        """Can schedule source sync with cron expression."""
        scheduler = SyncScheduler(db_session_factory=Mock())
        scheduler.start()
        
        job_id = scheduler.schedule_source_sync(
            source_id='test-source',
            cron_expression='0 2 * * *'  # Daily at 2am
        )
        
        assert job_id is not None
        assert 'test-source' in scheduler.sync_jobs
        
        scheduler.stop()
    
    def test_schedule_source_sync_requires_trigger(self):
        """Raises error if neither interval nor cron provided."""
        scheduler = SyncScheduler(db_session_factory=Mock())
        scheduler.start()
        
        with pytest.raises(ValueError, match="Must provide either"):
            scheduler.schedule_source_sync(source_id='test-source')
        
        scheduler.stop()
    
    def test_unschedule_source_sync(self):
        """Can unschedule source sync."""
        scheduler = SyncScheduler(db_session_factory=Mock())
        scheduler.start()
        
        scheduler.schedule_source_sync(
            source_id='test-source',
            interval_minutes=5
        )
        
        assert 'test-source' in scheduler.sync_jobs
        
        scheduler.unschedule_source_sync('test-source')
        assert 'test-source' not in scheduler.sync_jobs
        
        scheduler.stop()
    
    def test_get_scheduled_jobs(self):
        """Can get list of scheduled jobs."""
        scheduler = SyncScheduler(db_session_factory=Mock())
        scheduler.start()
        
        scheduler.schedule_source_sync(
            source_id='source1',
            interval_minutes=5
        )
        scheduler.schedule_source_sync(
            source_id='source2',
            interval_minutes=10
        )
        
        jobs = scheduler.get_scheduled_jobs()
        assert len(jobs) == 2
        
        scheduler.stop()
    
    @patch('ai_framework.core.sync.manager.StorageProviderFactory')
    def test_trigger_source_sync(self, mock_factory, sqlite_memory_db, test_source):
        """Can manually trigger source sync."""
        mock_provider = Mock()
        mock_provider.list_files.return_value = []
        mock_factory.create_from_knowledge_source.return_value = mock_provider
        
        scheduler = SyncScheduler(db_session_factory=lambda: sqlite_memory_db)
        result = scheduler.trigger_source_sync(test_source.id)
        
        assert result.status == "completed"


# ==================== SyncResult Tests ====================

class TestSyncResult:
    """Test sync result data class."""
    
    def test_sync_result_to_dict(self):
        """Can convert sync result to dictionary."""
        result = SyncResult()
        result.source_id = "test-source"
        result.started_at = datetime.utcnow()
        result.completed_at = datetime.utcnow()
        result.status = "completed"
        result.files_found = 10
        result.files_added = 5
        result.files_updated = 3
        result.files_deleted = 2
        result.errors = []
        
        data = result.to_dict()
        
        assert data['source_id'] == "test-source"
        assert data['status'] == "completed"
        assert data['files_found'] == 10
        assert data['files_added'] == 5
        assert data['files_updated'] == 3
        assert data['files_deleted'] == 2
        assert data['duration_seconds'] is not None


# ==================== Integration Tests ====================

class TestSyncIntegration:
    """Integration tests for sync system."""
    
    @patch('ai_framework.core.sync.manager.StorageProviderFactory')
    def test_complete_sync_workflow(self, mock_factory, sqlite_memory_db, test_source, mock_file_metadata):
        """Test complete sync workflow from start to finish."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.list_files.return_value = mock_file_metadata
        mock_factory.create_from_knowledge_source.return_value = mock_provider
        
        # 1. Initial sync - should add files
        manager = DocumentSyncManager(sqlite_memory_db)
        result1 = manager.sync_source(test_source.id)
        
        assert result1.files_added == 2
        assert result1.files_updated == 0
        assert result1.files_deleted == 0
        
        # 2. Second sync with no changes - should do nothing
        result2 = manager.sync_source(test_source.id)
        
        assert result2.files_added == 0
        assert result2.files_updated == 0
        assert result2.files_deleted == 0
        
        # 3. Update one file
        updated_file = mock_file_metadata[0]
        updated_file.modified_at = datetime.utcnow() + timedelta(seconds=10)
        updated_file.name = 'updated_name.pdf'
        mock_provider.list_files.return_value = [updated_file, mock_file_metadata[1]]
        
        result3 = manager.sync_source(test_source.id)
        
        assert result3.files_added == 0
        assert result3.files_updated == 1
        assert result3.files_deleted == 0
        
        # 4. Delete one file
        mock_provider.list_files.return_value = [updated_file]
        
        result4 = manager.sync_source(test_source.id)
        
        assert result4.files_added == 0
        assert result4.files_updated == 0
        assert result4.files_deleted == 1
        
        # Verify final state
        docs = sqlite_memory_db.query(KnowledgeDocument).filter_by(agent_id=test_source.agent_id).all()
        docs = [d for d in docs if d.attrs.get('source_db_id') == test_source.id]
        assert len(docs) == 1
        assert docs[0].file_name == 'updated_name.pdf'
