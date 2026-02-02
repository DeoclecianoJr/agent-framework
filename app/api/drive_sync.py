"""
Google Drive RAG Synchronization System.
Agent-specific folder configuration is done directly in agent definition, not via API.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.models import KnowledgeDocument, KnowledgeSource, Agent
from app.core.dependencies import get_db
from ai_framework.agent import AgentRegistry
import requests
import os
from typing import List, Dict, Any, Optional
import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from sentence_transformers import SentenceTransformer
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["drive-sync"])

# Global token storage (in production, use database)
stored_token = None
sync_status = {"running": False, "last_sync": None, "documents_count": 0, "errors": []}

class GoogleDriveSync:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {'Authorization': f'Bearer {access_token}'}
    
    def get_folder_id_by_name(self, folder_name: str) -> Optional[str]:
        """Find folder ID by name."""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            url = f'https://www.googleapis.com/drive/v3/files?q={query}&fields=files(id,name)'
            
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"Failed to search folder: {response.text}")
                return None
                
            data = response.json()
            folders = data.get('files', [])
            
            if not folders:
                logger.warning(f"Folder '{folder_name}' not found")
                return None
                
            return folders[0]['id']
            
        except Exception as e:
            logger.error(f"Error finding folder: {str(e)}")
            return None
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """List all files in a specific folder."""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            url = f'https://www.googleapis.com/drive/v3/files?q={query}&fields=files(id,name,mimeType,size,createdTime,modifiedTime)&pageSize=100'
            
            all_files = []
            
            while url:
                response = requests.get(url, headers=self.headers)
                if response.status_code != 200:
                    logger.error(f"Failed to list files: {response.text}")
                    break
                    
                data = response.json()
                files = data.get('files', [])
                all_files.extend(files)
                
                # Check for next page
                next_page_token = data.get('nextPageToken')
                if next_page_token:
                    url = f'https://www.googleapis.com/drive/v3/files?q={query}&fields=files(id,name,mimeType,size,createdTime,modifiedTime)&pageSize=100&pageToken={next_page_token}'
                else:
                    url = None
            
            logger.info(f"Found {len(all_files)} files in folder")
            return all_files
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def download_file_content(self, file_id: str, mime_type: str) -> Optional[str]:
        """Download and extract text content from a file."""
        try:
            # Handle different file types
            if 'google-apps.document' in mime_type:
                # Google Docs - export as plain text
                url = f'https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain'
            elif 'google-apps.spreadsheet' in mime_type:
                # Google Sheets - export as CSV
                url = f'https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/csv'
            elif 'google-apps.presentation' in mime_type:
                # Google Slides - export as plain text
                url = f'https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain'
            elif 'application/pdf' in mime_type:
                # PDF files - download binary content and extract text
                url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    # Extract text from PDF binary content
                    text_content = extract_text_from_pdf(response.content)
                    if text_content:
                        logger.info(f"Successfully extracted text from PDF")
                        return text_content
                    else:
                        logger.warning(f"Could not extract text from PDF")
                        return None
                else:
                    logger.error(f"Failed to download PDF (status {response.status_code}): {response.text}")
                    return None
            elif any(text_type in mime_type for text_type in ['text/', 'application/json', 'application/xml']):
                # Regular text files
                url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
            else:
                logger.warning(f"Unsupported file type: {mime_type}")
                return None
            
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                # Handle encoding properly
                content = response.text
                if not content.strip():  # Check if content is empty
                    logger.warning(f"File content is empty")
                    return None
                return content
            else:
                logger.error(f"Failed to download file content (status {response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading file content: {str(e)}")
            return None

def extract_text_from_pdf(pdf_content: bytes) -> Optional[str]:
    """Extract text from PDF binary content."""
    if PyPDF2 is None:
        logger.error("PyPDF2 not installed. Cannot extract PDF text.")
        return None
    
    try:
        # Create BytesIO object from binary content
        pdf_file = BytesIO(pdf_content)
        
        # Create PDF reader
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages
        text_content = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text.strip():  # Only add non-empty text
                text_content.append(text)
        
        if not text_content:
            logger.warning("No text found in PDF")
            return None
            
        # Join all pages with double newline
        full_text = "\n\n".join(text_content)
        logger.info(f"Extracted {len(full_text)} characters from PDF ({len(pdf_reader.pages)} pages)")
        return full_text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None


def extract_text_from_pdf(pdf_content: bytes) -> Optional[str]:
    """Extract text from PDF binary content."""
    if PyPDF2 is None:
        logger.error("PyPDF2 not installed. Cannot extract PDF text.")
        return None
    
    try:
        import re
        
        # Create BytesIO object from binary content
        pdf_file = BytesIO(pdf_content)
        
        # Create PDF reader
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages
        text_content = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text.strip():  # Only add non-empty text
                # Clean excessive whitespace from PDF extraction (multiple spaces/newlines → single space)
                text = re.sub(r'\s+', ' ', text).strip()
                text_content.append(text)
        
        if not text_content:
            logger.warning("No text found in PDF")
            return None
            
        # Join all pages with double newline
        full_text = "\n\n".join(text_content)
        logger.info(f"Extracted {len(full_text)} characters from PDF ({len(pdf_reader.pages)} pages)")
        return full_text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for RAG processing."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to end at a sentence or word boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            last_space = chunk.rfind(' ')
            
            boundary = max(last_period, last_newline, last_space)
            if boundary > start + chunk_size // 2:  # Don't make chunks too small
                chunk = text[start:start + boundary + 1]
                end = start + boundary + 1
        
        chunks.append(chunk.strip())
        start = max(start + chunk_size - overlap, end)
        
        if end >= len(text):
            break
    
    return chunks

# Global embedding model (load once, reuse for all chunks)
_embedding_model = None

def get_embedding_model():
    """Get or initialize the local embedding model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading multilingual embedding model: paraphrase-multilingual-MiniLM-L12-v2")
        _embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("✅ Local embedding model loaded successfully")
    return _embedding_model

def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding vector for text using local Sentence Transformers.
    
    Args:
        text: Text to generate embedding for
        
    Returns:
        Embedding vector as list of floats, or None if failed
    """
    try:
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return None
            
        model = get_embedding_model()
        
        # Generate embedding for the text (limit to avoid issues)
        text_chunk = text[:8000].strip()
        logger.info(f"Generating embedding for text chunk of {len(text_chunk)} chars")
        
        embedding = model.encode(text_chunk, convert_to_numpy=True)
        
        # Convert to list for JSON serialization
        embedding_list = embedding.tolist()
        
        logger.info(f"✅ Generated local embedding with {len(embedding_list)} dimensions")
        return embedding_list
        
    except Exception as e:
        logger.error(f"❌ Failed to generate local embedding: {e}", exc_info=True)
        return None

@router.post("/start")
def start_sync(agent_name: str, db: Session = Depends(get_db)):
    """Start Google Drive RAG synchronization for an agent with pre-configured folder."""
    global stored_token, sync_status
    
    if sync_status["running"]:
        raise HTTPException(status_code=409, detail="Sync already running")
    
    if not stored_token:
        return {
            "error": "No Google Drive token available",
            "message": "Run OAuth flow first",
            "oauth_url": "/google-drive-real/auth-start"
        }
    
    # Find agent in SDK registry (not database)
    try:
        agent_def = AgentRegistry.instance().get(agent_name)
    except KeyError:
        raise HTTPException(
            status_code=404, 
            detail=f"Agent '{agent_name}' not registered. Make sure the agent file is loaded and uses @agent decorator."
        )
    
    # Get drive folder from agent config
    drive_folder = agent_def.config.get("drive_folder")
    if not drive_folder:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{agent_name}' has no 'drive_folder' configured. Add drive_folder to agent config."
        )
    
    sync_status["running"] = True
    sync_status["errors"] = []
    
    try:
        logger.info(f"Starting sync for agent: {agent_name}, folder: {drive_folder}")
        
        # Initialize Google Drive sync
        drive_sync = GoogleDriveSync(stored_token)
        
        # Find folder by name
        folder_id = drive_sync.get_folder_id_by_name(drive_folder)
        if not folder_id:
            sync_status["running"] = False
            return {
                "error": f"Folder '{drive_folder}' not found in Google Drive",
                "message": f"Please create folder '{drive_folder}' in your Google Drive",
                "agent_config": f"Agent '{agent_name}' is configured to use folder: {drive_folder}"
            }
        
        # Create or update knowledge source
        knowledge_source = db.query(KnowledgeSource).filter(
            KnowledgeSource.agent_id == agent_name,
            KnowledgeSource.source_type == "google_drive"
        ).first()
        
        if not knowledge_source:
            knowledge_source = KnowledgeSource(
                id=str(uuid.uuid4()),
                agent_id=agent_name,
                source_type="google_drive",
                config={
                    "folder_id": folder_id, 
                    "folder_name": drive_folder,
                    "agent_name": agent_name
                },
                sync_status="running"
            )
            db.add(knowledge_source)
        else:
            knowledge_source.config = {
                "folder_id": folder_id, 
                "folder_name": drive_folder,
                "agent_name": agent_name
            }
            knowledge_source.sync_status = "running"
            knowledge_source.sync_errors = {}
        
        db.commit()
        
        # List files in folder
        files = drive_sync.list_files_in_folder(folder_id)
        
        processed_documents = []
        total_chunks = 0
        
        # Clean existing documents for this source
        db.query(KnowledgeDocument).filter(
            KnowledgeDocument.agent_id == agent_name,
            KnowledgeDocument.source_type == "google_drive",
            KnowledgeDocument.source_id.like(f"{folder_id}%")
        ).delete(synchronize_session=False)
        db.commit()
        
        for file_info in files:
            try:
                file_id = file_info['id']
                file_name = file_info['name']
                mime_type = file_info['mimeType']
                file_size = file_info.get('size', 'unknown')
                
                logger.info(f"Processing file: {file_name} (type: {mime_type}, size: {file_size})")
                
                # Download content
                content = drive_sync.download_file_content(file_id, mime_type)
                if not content:
                    error_msg = f"Could not download: {file_name} (type: {mime_type})"
                    sync_status["errors"].append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # Create chunks for RAG
                chunks = chunk_text(content, chunk_size=1000, overlap=200)
                total_chunks += len(chunks)
                
                logger.info(f"Processing {len(chunks)} chunks for {file_name}, generating embeddings...")
                
                # Save chunks to database with embeddings
                for i, chunk in enumerate(chunks):
                    # Generate embedding for this chunk
                    embedding = generate_embedding(chunk)
                    
                    knowledge_doc = KnowledgeDocument(
                        id=str(uuid.uuid4()),
                        agent_id=agent_name,
                        source_type="google_drive",
                        source_id=f"{folder_id}/{file_id}",
                        file_name=file_name,
                        content_chunk=chunk,
                        chunk_index=i,
                        embedding=embedding,  # ✅ Save embedding vector
                        attrs={
                            "mime_type": mime_type,
                            "file_size": file_info.get('size'),
                            "created_time": file_info.get('createdTime'),
                            "modified_time": file_info.get('modifiedTime'),
                            "folder_id": folder_id,
                            "folder_name": drive_folder,
                            "total_chunks": len(chunks),
                            "has_embedding": embedding is not None
                        }
                    )
                    db.add(knowledge_doc)
                
                # Commit after each file to avoid losing progress
                db.commit()
                logger.info(f"✅ Saved {len(chunks)} chunks with embeddings for {file_name}")
                
                # Document processing summary
                doc_info = {
                    "file_id": file_id,
                    "name": file_name,
                    "mime_type": mime_type,
                    "size": len(content),
                    "chunks_count": len(chunks),
                    "modified_time": file_info.get('modifiedTime'),
                    "created_time": file_info.get('createdTime')
                }
                
                processed_documents.append(doc_info)
                
            except Exception as e:
                error_msg = f"Error processing {file_info.get('name', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                sync_status["errors"].append(error_msg)
        
        # Update knowledge source status
        knowledge_source.sync_status = "completed" if not sync_status["errors"] else "completed_with_errors"
        knowledge_source.last_sync_at = datetime.now(timezone.utc)
        knowledge_source.sync_errors = {"errors": sync_status["errors"]} if sync_status["errors"] else {}
        db.commit()
        
        sync_status["running"] = False
        sync_status["last_sync"] = datetime.utcnow().isoformat()
        sync_status["documents_count"] = len(processed_documents)
        
        return {
            "status": "✅ Sync completed successfully",
            "agent": {
                "id": agent_name, 
                "name": agent_def.name,
                "configured_folder": drive_folder
            },
            "folder_name": drive_folder,
            "folder_id": folder_id,
            "summary": {
                "total_files": len(files),
                "processed_documents": len(processed_documents),
                "total_chunks_saved": total_chunks,
                "errors_count": len(sync_status["errors"])
            },
            "documents": processed_documents,
            "errors": sync_status["errors"],
            "database_info": {
                "agent_id": agent_name,
                "knowledge_source_id": knowledge_source.id,
                "chunks_in_database": total_chunks,
                "embeddings_generated": True,
                "rag_isolation": f"Documents isolated to agent '{agent_name}'"
            },
            "next_steps": [
                f"✅ {total_chunks} chunks saved with embeddings for agent '{agent_name}'",
                f"✅ Documents from '{drive_folder}' ready for semantic RAG queries",
                f"🔍 Agent '{agent_name}' can now use this knowledge in conversations",
                f"🎯 Embeddings generated locally using Sentence Transformers (paraphrase-multilingual-MiniLM-L12-v2)",
                "📊 Check /sync/status for synchronization status"
            ]
        }
        
    except Exception as e:
        sync_status["running"] = False
        error_msg = f"Sync failed: {str(e)}"
        logger.error(error_msg)
        sync_status["errors"].append(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/status")
def get_sync_status(db: Session = Depends(get_db)):
    """Get current synchronization status."""
    global sync_status, stored_token
    
    # Get database stats
    total_agents = db.query(Agent).count()
    total_knowledge_sources = db.query(KnowledgeSource).count()
    total_documents = db.query(KnowledgeDocument).count()
    
    # Get recent sync info
    recent_sources = db.query(KnowledgeSource).filter(
        KnowledgeSource.source_type == "google_drive"
    ).order_by(KnowledgeSource.last_sync_at.desc()).limit(5).all()
    
    return {
        "token_available": stored_token is not None,
        "sync_running": sync_status["running"],
        "last_sync": sync_status["last_sync"],
        "documents_count": sync_status["documents_count"],
        "errors": sync_status["errors"],
        "token_status": "✅ Connected" if stored_token else "❌ No token - run OAuth first",
        "database_stats": {
            "total_agents": total_agents,
            "total_knowledge_sources": total_knowledge_sources,
            "total_document_chunks": total_documents
        },
        "recent_syncs": [
            {
                "id": source.id,
                "agent_name": source.config.get("agent_name") if source.config else None,
                "folder_name": source.config.get("folder_name") if source.config else None,
                "folder_id": source.config.get("folder_id") if source.config else None,
                "status": source.sync_status,
                "last_sync": source.last_sync_at.isoformat() if source.last_sync_at else None,
                "errors": source.sync_errors
            }
            for source in recent_sources
        ],
        "instructions": [
            "📋 Configure agent with drive_folder in agent config (code)",
            "🚀 Run 'POST /sync/start?agent_name=AGENT_NAME' to synchronize",
            "🔍 Agent will use synchronized knowledge automatically in chat"
        ]
    }

def store_token(token: str):
    """Store token from OAuth callback (called internally)."""
    global stored_token
    stored_token = token
    logger.info("Google Drive token stored for sync system")