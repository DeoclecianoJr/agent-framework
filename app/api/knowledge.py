"""
Knowledge base API endpoints.

Story 7.7: Semantic Search API
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.dependencies import get_db
from app.core.models import KnowledgeDocument, KnowledgeSource, Agent
from app.schemas import (
    EmbedDocumentRequest,
    EmbedDocumentResponse,
    EmbedSourceRequest,
    EmbedSourceResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SearchResult
)
from ai_framework.core.embeddings import EmbeddingProviderFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/documents/{doc_id}/embed", response_model=EmbedDocumentResponse)
def embed_document(
    doc_id: str,
    request: EmbedDocumentRequest,
    db: Session = Depends(get_db)
):
    """
    Generate embedding for a specific document.
    
    Args:
        doc_id: Knowledge document ID
        request: Embedding request with provider config
        db: Database session
        
    Returns:
        EmbedDocumentResponse: Embedding result
        
    Raises:
        404: If document not found
        500: If embedding generation fails
    """
    # Get document
    document = db.query(KnowledgeDocument).filter_by(id=doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    
    # Check if document has content to embed
    if not document.content_chunk:
        raise HTTPException(
            status_code=400,
            detail="Document has no content chunk to embed. Run parsing first."
        )
    
    try:
        # Create embedding provider
        provider_type = request.provider or 'openai'
        provider = EmbeddingProviderFactory.create_provider(
            provider_type=provider_type,
            model=request.model
        )
        
        # Generate embedding
        result = provider.embed_text(document.content_chunk)
        
        # Update document with embedding
        document.embedding = result.embedding
        db.commit()
        
        logger.info(
            f"Generated embedding for document {doc_id} "
            f"using {provider_type}/{result.model}"
        )
        
        return EmbedDocumentResponse(
            document_id=doc_id,
            model=result.model,
            dimension=len(result.embedding),
            tokens=result.tokens,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Failed to embed document {doc_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@router.post("/sources/{source_id}/embed", response_model=EmbedSourceResponse)
def embed_source(
    source_id: str,
    request: EmbedSourceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate embeddings for all documents in a knowledge source.
    
    This endpoint queues a background task to generate embeddings for all
    documents associated with the source. Use GET /api/knowledge/sources/{source_id}/status
    to check progress.
    
    Args:
        source_id: Knowledge source ID
        request: Embedding request
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        EmbedSourceResponse: Task status
        
    Raises:
        404: If source not found
    """
    # Get source
    source = db.query(KnowledgeSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    
    # Count documents to embed
    docs_query = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.attrs['source_db_id'].astext == source_id,
        KnowledgeDocument.content_chunk.isnot(None)
    )
    
    total_documents = docs_query.count()
    
    if total_documents == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents with content found in this source"
        )
    
    # Queue background task
    background_tasks.add_task(
        _embed_source_background,
        source_id,
        request.provider or 'openai',
        request.model,
        request.batch_size or 100
    )
    
    return EmbedSourceResponse(
        source_id=source_id,
        total_documents=total_documents,
        status="queued",
        message=f"Embedding task queued for {total_documents} documents"
    )


def _embed_source_background(
    source_id: str,
    provider_type: str,
    model: Optional[str],
    batch_size: int
):
    """
    Background task to embed all documents in a source.
    
    Args:
        source_id: Knowledge source ID
        provider_type: Embedding provider type
        model: Model name
        batch_size: Batch size for embedding
    """
    from app.main import SessionLocal
    
    db = SessionLocal()
    
    try:
        # Create provider
        provider = EmbeddingProviderFactory.create_provider(
            provider_type=provider_type,
            model=model
        )
        
        # Get documents without embeddings
        documents = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.attrs['source_db_id'].astext == source_id,
            KnowledgeDocument.content_chunk.isnot(None),
            KnowledgeDocument.embedding.is_(None)
        ).all()
        
        logger.info(f"Embedding {len(documents)} documents from source {source_id}")
        
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            texts = [doc.content_chunk for doc in batch]
            
            # Generate embeddings
            results = provider.embed_batch(texts)
            
            # Update documents
            for doc, result in zip(batch, results):
                doc.embedding = result.embedding
            
            db.commit()
            logger.info(f"Embedded batch {i//batch_size + 1} ({len(batch)} documents)")
        
        logger.info(f"Completed embedding for source {source_id}")
        
    except Exception as e:
        logger.error(f"Background embedding failed for source {source_id}: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/search", response_model=SemanticSearchResponse)
def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Perform semantic search across knowledge base.
    
    Uses pgvector cosine similarity to find the most relevant document chunks
    for a given query.
    
    Args:
        request: Search request with query and parameters
        db: Database session
        
    Returns:
        SemanticSearchResponse: Ranked search results
        
    Raises:
        400: If invalid parameters
        500: If search fails
    """
    try:
        # Create embedding provider
        provider_type = request.provider or 'openai'
        provider = EmbeddingProviderFactory.create_provider(
            provider_type=provider_type,
            model=request.model
        )
        
        # Generate query embedding
        query_result = provider.embed_text(request.query)
        query_embedding = query_result.embedding
        
        # Build base query
        query = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.embedding.isnot(None)
        )
        
        # Filter by agent if specified
        if request.agent_id:
            # Get sources for agent
            from app.core.models import KnowledgeSource
            source_ids = [
                s.id for s in db.query(KnowledgeSource).filter_by(
                    agent_id=request.agent_id
                ).all()
            ]
            
            if source_ids:
                query = query.filter(
                    KnowledgeDocument.attrs['source_db_id'].astext.in_(source_ids)
                )
        
        # Perform vector similarity search using pgvector
        # Using cosine distance operator: <=>
        from sqlalchemy import func, cast
        from sqlalchemy.dialects.postgresql import ARRAY
        from pgvector.sqlalchemy import Vector
        
        # Convert query embedding to pgvector format
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Order by cosine similarity (lower distance = more similar)
        query = query.order_by(
            KnowledgeDocument.embedding.cosine_distance(embedding_str)
        ).limit(request.top_k or 10)
        
        # Execute query
        documents = query.all()
        
        # Build results
        results = []
        for doc in documents:
            # Calculate similarity score (1 - cosine_distance)
            distance = doc.embedding.cosine_distance(embedding_str)
            score = 1 - float(distance) if distance is not None else 0.0
            
            # Skip if below minimum score
            if request.min_score and score < request.min_score:
                continue
            
            results.append(SearchResult(
                document_id=doc.id,
                file_name=doc.file_name,
                content=doc.content_chunk[:500] if doc.content_chunk else "",
                score=score,
                metadata={
                    'source_id': doc.attrs.get('source_db_id'),
                    'source_type': doc.source_type,
                    'chunk_index': doc.attrs.get('chunk_index'),
                    'mime_type': doc.attrs.get('mime_type'),
                }
            ))
        
        logger.info(f"Semantic search returned {len(results)} results")
        
        return SemanticSearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            model=query_result.model
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
