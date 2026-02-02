"""
Real Google Drive integration for RAG testing.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
import os
from typing import Optional
import json

# Try to import Google libraries (might not be installed in prod yet)
try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

router = APIRouter(prefix="/google-drive-real", tags=["google-drive-real"])

# Criar router adicional para /api (compatibilidade com Google OAuth redirect URI)
oauth_router = APIRouter(prefix="/api", tags=["oauth"])

@router.get("/test-credentials")
def test_credentials():
    """Test if Google credentials are properly configured."""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET') 
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    
    return {
        "google_libraries_available": GOOGLE_AVAILABLE,
        "credentials_configured": bool(client_id and client_secret and redirect_uri),
        "client_id": client_id[:20] + "..." if client_id else None,
        "redirect_uri": redirect_uri,
        "ready_for_oauth": GOOGLE_AVAILABLE and bool(client_id and client_secret and redirect_uri)
    }

@router.post("/auth-start")  
def start_auth():
    """Start real Google Drive OAuth2 flow."""
    if not GOOGLE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google libraries não instaladas")
    
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    
    if not all([client_id, client_secret, redirect_uri]):
        raise HTTPException(status_code=500, detail="Credenciais Google não configuradas")
    
    try:
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/drive.metadata.readonly',
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/userinfo.email',
                'openid'
            ]
        )
        flow.redirect_uri = redirect_uri
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return {
            "status": "ready",
            "auth_url": auth_url,
            "state": state,
            "instructions": [
                "1. Copie a auth_url",
                "2. Abra em um navegador", 
                "3. Faça login na sua conta Google",
                "4. Autorize o aplicativo",
                "5. Você será redirecionado de volta"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar OAuth: {str(e)}")

def oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Handle Google OAuth callback."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"OAuth callback received - code: {code[:20] if code else None}..., state: {state}, error: {error}")
    
    if error:
        return {"error": f"OAuth falhou: {error}"}
    
    if not code:
        return {"error": "Código de autorização não recebido"}
    
    if not GOOGLE_AVAILABLE:
        return {"error": "Google libraries não disponíveis"}
    
    try:
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        
        logger.info(f"Using redirect_uri: {redirect_uri}")
        
        # Create OAuth2 flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/drive.metadata.readonly',
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/userinfo.email',
                'openid'
            ],
            state=state  # Use the state from the callback
        )
        flow.redirect_uri = redirect_uri
        
        logger.info(f"Attempting to fetch token with code...")
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        logger.info("Token fetched successfully!")
        
        credentials = flow.credentials
        
        # Store token for drive_sync to use
        from app.api import drive_sync
        drive_sync.stored_token = credentials.token
        logger.info(f"Token stored globally for sync operations")
        
        # Test Drive access
        service = build('drive', 'v3', credentials=credentials)
        about = service.about().get(fields="user,storageQuota").execute()
        
        # List some files
        results = service.files().list(pageSize=5, fields="files(id,name,mimeType,size)").execute()
        files = results.get('files', [])
        
        return {
            "status": "✅ SUCESSO - Conectado ao Google Drive real!",
            "user_info": {
                "email": about.get('user', {}).get('emailAddress'),
                "name": about.get('user', {}).get('displayName')
            },
            "storage_info": {
                "used": about.get('storageQuota', {}).get('usage'),
                "limit": about.get('storageQuota', {}).get('limit')
            },
            "sample_files": [
                {
                    "id": f.get('id'),
                    "name": f.get('name'), 
                    "type": f.get('mimeType'),
                    "size": f.get('size', 'N/A')
                } for f in files
            ],
            "tokens": {
                "access_token": credentials.token[:20] + "...",
                "has_refresh": bool(credentials.refresh_token)
            }
        }
        
    except Exception as e:
        return {"error": f"Erro no callback: {str(e)}"}

@router.get("/list-files")
def list_files(access_token: str = Query(..., description="Token obtido no callback")):
    """List files from Google Drive using access token."""
    if not GOOGLE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google libraries não disponíveis")
    
    try:
        from google.oauth2.credentials import Credentials
        
        credentials = Credentials(token=access_token)
        service = build('drive', 'v3', credentials=credentials)
        
        # List files with details
        results = service.files().list(
            pageSize=20, 
            fields="files(id,name,mimeType,size,modifiedTime,webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        
        # Filter for RAG-compatible files
        rag_files = []
        for file in files:
            mime_type = file.get('mimeType', '')
            if any(t in mime_type for t in ['text', 'pdf', 'document', 'presentation']):
                rag_files.append({
                    "id": file.get('id'),
                    "name": file.get('name'),
                    "type": mime_type,
                    "size": file.get('size', 'N/A'),
                    "modified": file.get('modifiedTime'),
                    "view_url": file.get('webViewLink'),
                    "rag_compatible": True
                })
        
        return {
            "status": "success",
            "total_files": len(files),
            "rag_compatible_files": len(rag_files), 
            "files": rag_files[:10],  # First 10 for display
            "message": f"Encontrados {len(rag_files)} arquivos compatíveis com RAG"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")


# Duplicate callback endpoint at /api/oauth/callback (for Google OAuth redirect URI)
@oauth_router.get("/oauth/callback")
def api_oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Handle Google OAuth callback at /api/oauth/callback endpoint."""
    return oauth_callback(code=code, state=state, error=error)