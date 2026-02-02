"""
Document Sync Manager.

Orchestrates synchronization of documents from cloud storage providers
to the knowledge base with change detection and state tracking.

Story 7.5: Document Sync Scheduler
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.models import KnowledgeSource, KnowledgeDocument
from ai_framework.core.storage import StorageProviderFactory, FileMetadata
from ai_framework.core.parsing import ParserFactory, TextChunker

logger = logging.getLogger(__name__)


class SyncResult:
    """Result of a sync operation."""
    
    def __init__(self):
        self.source_id: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.status: str = "pending"  # pending, running, completed, failed
        self.files_found: int = 0
        self.files_added: int = 0
        self.files_updated: int = 0
        self.files_deleted: int = 0
        self.errors: List[str] = []
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'source_id': self.source_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'files_found': self.files_found,
            'files_added': self.files_added,
            'files_updated': self.files_updated,
            'files_deleted': self.files_deleted,
            'errors': self.errors,
            'duration_seconds': (
                (self.completed_at - self.started_at).total_seconds() 
                if self.started_at and self.completed_at else None
            )
        }


class DocumentSyncManager:
    """
    Manages document synchronization from cloud storage to knowledge base.
    
    Features:
    - Change detection (new, updated, deleted files)
    - Incremental sync based on last_sync_at
    - Error handling and retry logic
    - Sync status tracking
    
    Usage:
        manager = DocumentSyncManager(db)
        result = manager.sync_source(source_id)
        print(f"Added: {result.files_added}, Updated: {result.files_updated}")
    """
    
    def __init__(
        self, 
        db: Session, 
        enable_parsing: bool = True,
        enable_embeddings: bool = True,
        embedding_provider: str = 'local',
        embedding_model: str = None
    ):
        """
        Initialize sync manager.
        
        Args:
            db: Database session
            enable_parsing: Enable document parsing and chunking
            enable_embeddings: Enable automatic embedding generation (default: True)
            embedding_provider: Embedding provider to use ('local', 'openai', 'gemini')
            embedding_model: Model name (provider default if None)
        """
        self.db = db
        self.enable_parsing = enable_parsing
        self.enable_embeddings = enable_embeddings
        self.chunker = TextChunker(chunk_size=512, overlap=50) if enable_parsing else None
        
        # Initialize embedding provider if enabled
        self.embedding_provider_instance = None
        if enable_embeddings:
            from ai_framework.core.embeddings import EmbeddingProviderFactory
            self.embedding_provider_instance = EmbeddingProviderFactory.create_provider(
                provider_type=embedding_provider,
                model=embedding_model
            )
            logger.info(f"Sync manager: Embeddings enabled with {embedding_provider}/{self.embedding_provider_instance.model}")
    
    def sync_source(
        self,
        source_id: str,
        force_full_sync: bool = False
    ) -> SyncResult:
        """
        Sync documents from a knowledge source.
        
        Args:
            source_id: KnowledgeSource ID
            force_full_sync: Force full sync ignoring last_sync_at
            
        Returns:
            SyncResult: Sync operation result
        """
        result = SyncResult()
        result.source_id = source_id
        result.started_at = datetime.utcnow()
        result.status = "running"
        
        try:
            # Get knowledge source
            source = self.db.query(KnowledgeSource).filter_by(id=source_id).first()
            if not source:
                result.status = "failed"
                result.errors.append(f"Source {source_id} not found")
                return result
            
            logger.info(f"Starting sync for source {source_id} (agent: {source.agent_id})")
            
            # Create storage provider
            provider = StorageProviderFactory.create_from_knowledge_source(
                self.db,
                source_id,
                auto_authenticate=True
            )
            
            # Get files from provider
            files = provider.list_files()
            result.files_found = len(files)
            
            logger.info(f"Found {len(files)} files in source {source_id}")
            
            # Get existing documents
            existing_docs = self._get_existing_documents(source_id)
            # Note: doc.source_id contains the file ID from storage provider
            existing_file_ids = {doc.source_id for doc in existing_docs}
            
            # Detect changes
            changes = self._detect_changes(
                files,
                existing_docs,
                source.last_sync_at if not force_full_sync else None
            )
            
            # Process new files
            for file_meta in changes['new']:
                try:
                    docs = self._create_document(source, file_meta)
                    result.files_added += len(docs)
                except Exception as e:
                    logger.error(f"Failed to add file {file_meta.id}: {e}")
                    result.errors.append(f"Add failed for {file_meta.name}: {str(e)}")
            
            # Process updated files
            for file_meta, existing_doc in changes['updated']:
                try:
                    self._update_document(existing_doc, file_meta)
                    result.files_updated += 1
                except Exception as e:
                    logger.error(f"Failed to update file {file_meta.id}: {e}")
                    result.errors.append(f"Update failed for {file_meta.name}: {str(e)}")
            
            # Process deleted files
            for doc in changes['deleted']:
                try:
                    self.db.delete(doc)
                    result.files_deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete document {doc.id}: {e}")
                    result.errors.append(f"Delete failed for {doc.title}: {str(e)}")
            
            # Update source sync status
            source.last_sync_at = datetime.utcnow()
            source.sync_status = 'completed' if not result.errors else 'completed_with_errors'
            self.db.commit()
            
            result.status = "completed"
            result.completed_at = datetime.utcnow()
            
            logger.info(
                f"Sync completed for source {source_id}: "
                f"+{result.files_added} ~{result.files_updated} -{result.files_deleted}"
            )
            
        except Exception as e:
            logger.error(f"Sync failed for source {source_id}: {e}")
            result.status = "failed"
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            
            # Update source sync status
            try:
                source = self.db.query(KnowledgeSource).filter_by(id=source_id).first()
                if source:
                    source.sync_status = 'failed'
                    self.db.commit()
            except:
                pass
        
        return result
    
    def sync_all_sources(
        self,
        agent_id: Optional[str] = None
    ) -> List[SyncResult]:
        """
        Sync all knowledge sources.
        
        Args:
            agent_id: Optional filter by agent ID
            
        Returns:
            List[SyncResult]: Results for each source
        """
        query = self.db.query(KnowledgeSource)
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        
        sources = query.all()
        results = []
        
        for source in sources:
            result = self.sync_source(source.id)
            results.append(result)
        
        return results
    
    def _get_existing_documents(self, source_id: str) -> List[KnowledgeDocument]:
        """
        Get existing documents for a source.
        
        Note: We filter by attrs->source_db_id because source_id field
        contains the file ID from storage provider, not the KnowledgeSource ID.
        """
        # Get all documents for the agent and filter by source_db_id in attrs
        all_docs = self.db.query(KnowledgeDocument).all()
        return [
            doc for doc in all_docs
            if isinstance(doc.attrs, dict) and doc.attrs.get('source_db_id') == source_id
        ]
    
    def _detect_changes(
        self,
        remote_files: List[FileMetadata],
        local_docs: List[KnowledgeDocument],
        last_sync_at: Optional[datetime]
    ) -> Dict[str, List]:
        """
        Detect new, updated, and deleted files.
        
        Args:
            remote_files: Files from cloud storage
            local_docs: Existing documents in database
            last_sync_at: Last sync timestamp
            
        Returns:
            Dict with 'new', 'updated', 'deleted' lists
        """
        # Create lookup maps
        # Note: doc.source_id contains the file ID from storage provider
        remote_by_id = {f.id: f for f in remote_files}
        local_by_file_id = {doc.source_id: doc for doc in local_docs}
        
        new_files = []
        updated_files = []
        deleted_docs = []
        
        # Detect new and updated files
        for file_meta in remote_files:
            if file_meta.id not in local_by_file_id:
                # New file
                new_files.append(file_meta)
            else:
                # Existing file - check if modified
                local_doc = local_by_file_id[file_meta.id]
                
                # Compare modified timestamps
                if file_meta.modified_at and local_doc.updated_at:
                    # Remove timezone info for comparison
                    remote_modified = file_meta.modified_at.replace(tzinfo=None)
                    local_modified = local_doc.updated_at.replace(tzinfo=None)
                    
                    if remote_modified > local_modified:
                        updated_files.append((file_meta, local_doc))
        
        # Detect deleted files
        # Note: doc.source_id contains the file ID from storage provider
        for doc in local_docs:
            if doc.source_id not in remote_by_id:
                deleted_docs.append(doc)
        
        logger.info(
            f"Changes detected: {len(new_files)} new, "
            f"{len(updated_files)} updated, {len(deleted_docs)} deleted"
        )
        
        return {
            'new': new_files,
            'updated': updated_files,
            'deleted': deleted_docs
        }
    
    def _create_document(
        self,
        source: KnowledgeSource,
        file_meta: FileMetadata
    ) -> List[KnowledgeDocument]:
        """
        Create new knowledge document(s) from file.
        
        If parsing is enabled, downloads file, extracts text, and creates
        multiple documents (one per chunk).
        
        Args:
            source: Knowledge source
            file_meta: File metadata from storage provider
            
        Returns:
            List[KnowledgeDocument]: Created document(s)
        """
        created_docs = []
        
        # Skip folders
        if file_meta.is_folder:
            logger.debug(f"Skipping folder: {file_meta.name}")
            return created_docs
        
        # Check if we can parse this file type
        can_parse = (
            self.enable_parsing 
            and file_meta.mime_type 
            and ParserFactory.can_parse(file_meta.mime_type)
        )
        
        if can_parse:
            # Download, parse, and chunk the file
            try:
                created_docs = self._parse_and_chunk_file(source, file_meta)
                logger.info(
                    f"Parsed and chunked {file_meta.name}: "
                    f"{len(created_docs)} chunks created"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to parse {file_meta.name}, creating placeholder: {e}"
                )
                # Fallback to placeholder
                doc = self._create_placeholder_document(source, file_meta)
                created_docs = [doc]
        else:
            # Create placeholder document (no content)
            doc = self._create_placeholder_document(source, file_meta)
            created_docs = [doc]
        
        return created_docs
    
    def _parse_and_chunk_file(
        self,
        source: KnowledgeSource,
        file_meta: FileMetadata
    ) -> List[KnowledgeDocument]:
        """
        Download file, parse content, and create chunked documents.
        
        Args:
            source: Knowledge source
            file_meta: File metadata
            
        Returns:
            List[KnowledgeDocument]: Document chunks
        """
        # Get storage provider
        provider = StorageProviderFactory.create_from_knowledge_source(
            self.db,
            source.id,
            auto_authenticate=True
        )
        
        # Download file content
        content_stream = provider.download_file(file_meta.id)
        
        # Get parser for MIME type
        parser = ParserFactory.get_parser(file_meta.mime_type)
        if not parser:
            raise ValueError(f"No parser for MIME type: {file_meta.mime_type}")
        
        # Extract text
        text = parser.parse(content_stream)
        
        if not text or not text.strip():
            raise ValueError("No text content extracted from file")
        
        # Chunk text
        chunks = self.chunker.chunk(
            text,
            metadata={
                'file_name': file_meta.name,
                'mime_type': file_meta.mime_type,
                'source_db_id': source.id
            }
        )
        
        # Create document for each chunk
        docs = []
        for chunk_data in chunks:
            doc = KnowledgeDocument(
                agent_id=source.agent_id,
                source_id=file_meta.id,  # File ID from storage provider
                source_type=source.source_type,
                file_name=file_meta.name,
                content_chunk=chunk_data['text'],
                chunk_index=chunk_data['chunk_index'],
                attrs={
                    'source_db_id': source.id,
                    'mime_type': file_meta.mime_type,
                    'size': file_meta.size,
                    'web_url': file_meta.web_url,
                    'modified_at': file_meta.modified_at.isoformat() if file_meta.modified_at else None,
                    'is_folder': file_meta.is_folder,
                    'path': file_meta.path,
                    'token_count': chunk_data['token_count'],
                    'char_count': chunk_data['char_count'],
                    'total_chunks': len(chunks),
                    **file_meta.extra
                }
            )
            
            # Set updated_at to match file's modified time
            if file_meta.modified_at:
                doc.updated_at = file_meta.modified_at
            
            self.db.add(doc)
            docs.append(doc)
        
        self.db.flush()
        
        # Generate embeddings if enabled
        if self.enable_embeddings and self.embedding_provider_instance:
            self._generate_embeddings_for_chunks(docs)
        
        return docs
    
    def _create_placeholder_document(
        self,
        source: KnowledgeSource,
        file_meta: FileMetadata
    ) -> KnowledgeDocument:
        """
        Create placeholder document (no content).
        
        Used when parsing is disabled or file type is not supported.
        """
        doc = KnowledgeDocument(
            agent_id=source.agent_id,
            source_id=file_meta.id,  # File ID from storage provider
            source_type=source.source_type,
            file_name=file_meta.name,
            content_chunk="",  # Empty until parsed
            chunk_index=0,
            attrs={
                'source_db_id': source.id,  # Track which KnowledgeSource this came from
                'mime_type': file_meta.mime_type,
                'size': file_meta.size,
                'web_url': file_meta.web_url,
                'modified_at': file_meta.modified_at.isoformat() if file_meta.modified_at else None,
                'is_folder': file_meta.is_folder,
                'path': file_meta.path,
                **file_meta.extra
            }
        )
        
        # Set updated_at to match file's modified time for proper change detection
        if file_meta.modified_at:
            doc.updated_at = file_meta.modified_at
        
        self.db.add(doc)
        self.db.flush()  # Get ID without committing
        
        logger.debug(f"Created placeholder document {doc.id} for file {file_meta.name}")
        return doc
    
    def _update_document(
        self,
        doc: KnowledgeDocument,
        file_meta: FileMetadata
    ):
        """
        Update existing knowledge document.
        
        Args:
            doc: Existing document
            file_meta: Updated file metadata
        """
        doc.file_name = file_meta.name
        doc.attrs = {
            'source_db_id': doc.attrs.get('source_db_id'),  # Preserve source ID
            'mime_type': file_meta.mime_type,
            'size': file_meta.size,
            'web_url': file_meta.web_url,
            'modified_at': file_meta.modified_at.isoformat() if file_meta.modified_at else None,
            'is_folder': file_meta.is_folder,
            'path': file_meta.path,
            **file_meta.extra
        }
        # Set updated_at to match the remote file's modified time
        # This ensures we don't re-detect the same file as updated on next sync
        if file_meta.modified_at:
            doc.updated_at = file_meta.modified_at
    
    def _generate_embeddings_for_chunks(self, docs: List[KnowledgeDocument]):
        """
        Generate embeddings for document chunks in batch.
        
        Args:
            docs: List of documents to generate embeddings for
        """
        if not docs:
            return
        
        try:
            # Extract text from chunks
            texts = [doc.content_chunk for doc in docs if doc.content_chunk]
            
            if not texts:
                logger.warning("No text content to embed")
                return
            
            # Generate embeddings in batch
            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            results = self.embedding_provider_instance.embed_batch(texts)
            
            # Update documents with embeddings
            for doc, result in zip(docs, results):
                if doc.content_chunk:  # Only if we embedded it
                    doc.embedding = result.embedding
            
            logger.info(f"Successfully generated {len(results)} embeddings")
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Don't fail the sync, just log the error
        else:
            doc.updated_at = datetime.utcnow()
        
        logger.debug(f"Updated document {doc.id} for file {file_meta.name}")
