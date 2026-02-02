"""
Google Drive Storage Provider Implementation.

Implements CloudStorageProvider interface for Google Drive API v3.

Story 7.3: Google Drive OAuth 2.0 Integration
"""

import io
import logging
from typing import List, Optional, BinaryIO
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .base import (
    CloudStorageProvider,
    FileMetadata,
    StorageCredentials,
    StorageError,
    AuthenticationError,
    FileNotFoundError as StorageFileNotFoundError
)
from .oauth import OAuthManager

logger = logging.getLogger(__name__)


class GoogleDriveProvider(CloudStorageProvider):
    """
    Google Drive implementation of CloudStorageProvider.
    
    Features:
    - OAuth 2.0 authentication
    - List files and folders
    - Download files
    - Search with Google Drive query syntax
    - Automatic token refresh
    
    Usage:
        # Initialize with OAuth manager
        oauth = OAuthManager(OAuthManager.create_google_drive_config())
        
        # Get credentials from OAuth flow
        credentials = oauth.exchange_code(authorization_code)
        
        # Create provider
        drive = GoogleDriveProvider(credentials)
        drive.authenticate(credentials)
        
        # List files
        files = drive.list_files()
        
        # Download a file
        content = drive.download_file(file_id)
    """
    
    @property
    def provider_type(self) -> str:
        """Return provider type identifier."""
        return "google_drive"
    
    def __init__(self, credentials: Optional[StorageCredentials] = None):
        """
        Initialize Google Drive provider.
        
        Args:
            credentials: OAuth credentials
        """
        super().__init__(credentials)
        self.service = None
        self._oauth_manager = None
    
    def authenticate(self, credentials: StorageCredentials) -> bool:
        """
        Authenticate with Google Drive API.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            bool: True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Convert StorageCredentials to Google Credentials
            google_creds = self._convert_to_google_credentials(credentials)
            
            # Build Google Drive service
            self.service = build('drive', 'v3', credentials=google_creds)
            
            # Test authentication by listing files
            self.service.files().list(pageSize=1).execute()
            
            self.credentials = credentials
            self._authenticated = True
            logger.info("Google Drive: Successfully authenticated")
            return True
            
        except Exception as e:
            logger.error(f"Google Drive: Authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate with Google Drive: {e}")
    
    def refresh_credentials(self) -> StorageCredentials:
        """
        Refresh expired OAuth tokens.
        
        Returns:
            StorageCredentials: New credentials with refreshed tokens
            
        Raises:
            AuthenticationError: If refresh fails
        """
        if not self._oauth_manager:
            # Initialize OAuth manager if not set
            self._oauth_manager = OAuthManager(OAuthManager.create_google_drive_config())
        
        new_credentials = self._oauth_manager.refresh_token(self.credentials)
        
        # Re-authenticate with new credentials
        self.authenticate(new_credentials)
        
        return new_credentials
    
    def list_files(
        self,
        folder_id: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 100,
        file_types: Optional[List[str]] = None
    ) -> List[FileMetadata]:
        """
        List files in Google Drive.
        
        Args:
            folder_id: Folder ID to list files from (None = root)
            query: Google Drive query string
            page_size: Maximum number of files to return
            file_types: Filter by MIME types
            
        Returns:
            List[FileMetadata]: List of file metadata
            
        Raises:
            StorageError: If listing fails
        """
        self._ensure_authenticated()
        
        try:
            # Build query
            q_parts = []
            
            if folder_id:
                q_parts.append(f"'{folder_id}' in parents")
            
            if file_types:
                mime_conditions = " or ".join([f"mimeType='{mt}'" for mt in file_types])
                q_parts.append(f"({mime_conditions})")
            
            # Exclude trashed files
            q_parts.append("trashed=false")
            
            # Add custom query
            if query:
                q_parts.append(query)
            
            q = " and ".join(q_parts)
            
            # Execute query
            results = self.service.files().list(
                q=q,
                pageSize=page_size,
                fields="files(id, name, mimeType, size, modifiedTime, createdTime, "
                       "webViewLink, parents, description)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            # Convert to FileMetadata
            file_metadata_list = []
            for file_data in files:
                metadata = self._convert_to_file_metadata(file_data)
                file_metadata_list.append(metadata)
            
            logger.info(f"Google Drive: Listed {len(file_metadata_list)} files")
            return file_metadata_list
            
        except Exception as e:
            logger.error(f"Google Drive: Failed to list files: {e}")
            raise StorageError(f"Failed to list files: {e}")
    
    def get_file_metadata(self, file_id: str) -> FileMetadata:
        """
        Get metadata for a specific file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            FileMetadata: File metadata
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If retrieval fails
        """
        self._ensure_authenticated()
        
        try:
            file_data = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, createdTime, "
                       "webViewLink, parents, description"
            ).execute()
            
            metadata = self._convert_to_file_metadata(file_data)
            logger.info(f"Google Drive: Retrieved metadata for file {file_id}")
            return metadata
            
        except Exception as e:
            if "File not found" in str(e):
                raise StorageFileNotFoundError(f"File {file_id} not found")
            logger.error(f"Google Drive: Failed to get file metadata: {e}")
            raise StorageError(f"Failed to get file metadata: {e}")
    
    def download_file(self, file_id: str) -> bytes:
        """
        Download file content as bytes.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            bytes: File content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If download fails
        """
        self._ensure_authenticated()
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            
            content = file_buffer.getvalue()
            logger.info(f"Google Drive: Downloaded file {file_id} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            if "File not found" in str(e):
                raise StorageFileNotFoundError(f"File {file_id} not found")
            logger.error(f"Google Drive: Failed to download file: {e}")
            raise StorageError(f"Failed to download file: {e}")
    
    def download_file_stream(self, file_id: str) -> BinaryIO:
        """
        Download file as a stream.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            BinaryIO: File content stream
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If download fails
        """
        # For Google Drive, we download to BytesIO and return it
        # In production, could use chunked streaming for very large files
        content = self.download_file(file_id)
        return io.BytesIO(content)
    
    def _ensure_authenticated(self):
        """Ensure provider is authenticated."""
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with Google Drive")
        
        # Validate and refresh if needed
        if not self.validate_credentials():
            raise AuthenticationError("Invalid or expired credentials")
    
    def _convert_to_google_credentials(self, credentials: StorageCredentials) -> Credentials:
        """
        Convert StorageCredentials to Google Credentials object.
        
        Args:
            credentials: Storage credentials
            
        Returns:
            Credentials: Google OAuth credentials
        """
        return Credentials(
            token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri or 'https://oauth2.googleapis.com/token',
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )
    
    def _convert_to_file_metadata(self, file_data: dict) -> FileMetadata:
        """
        Convert Google Drive file data to FileMetadata.
        
        Args:
            file_data: File data from Google Drive API
            
        Returns:
            FileMetadata: Standardized file metadata
        """
        # Parse timestamps
        modified_at = datetime.fromisoformat(
            file_data['modifiedTime'].replace('Z', '+00:00')
        )
        created_at = None
        if file_data.get('createdTime'):
            created_at = datetime.fromisoformat(
                file_data['createdTime'].replace('Z', '+00:00')
            )
        
        # Check if folder
        is_folder = file_data.get('mimeType') == 'application/vnd.google-apps.folder'
        
        # Get parent folder
        parent_id = None
        if file_data.get('parents'):
            parent_id = file_data['parents'][0]
        
        return FileMetadata(
            id=file_data['id'],
            name=file_data['name'],
            mime_type=file_data.get('mimeType', 'application/octet-stream'),
            size=int(file_data.get('size', 0)),
            modified_at=modified_at,
            created_at=created_at,
            web_url=file_data.get('webViewLink'),
            parent_id=parent_id,
            is_folder=is_folder,
            extra={
                'description': file_data.get('description'),
                'google_apps_type': file_data.get('mimeType')
            }
        )
