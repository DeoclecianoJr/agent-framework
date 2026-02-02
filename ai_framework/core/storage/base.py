"""
Abstract Base Classes for Cloud Storage Providers.

This module defines the interface that all cloud storage providers must implement.
Supports: Google Drive, SharePoint, Dropbox, and future providers.

Story 7.3: Cloud Storage Integration (Abstracted Architecture)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    """
    Standardized file metadata across all storage providers.
    
    Attributes:
        id: Unique file identifier in the provider's system
        name: File name
        mime_type: MIME type (e.g., 'application/pdf')
        size: File size in bytes
        modified_at: Last modification timestamp
        created_at: Creation timestamp
        path: Full path or location in the storage
        web_url: Web URL to view the file (if available)
        parent_id: Parent folder ID (if applicable)
        is_folder: Whether this is a folder/directory
        extra: Provider-specific metadata
    """
    id: str
    name: str
    mime_type: str
    size: int
    modified_at: datetime
    created_at: Optional[datetime] = None
    path: Optional[str] = None
    web_url: Optional[str] = None
    parent_id: Optional[str] = None
    is_folder: bool = False
    extra: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


@dataclass
class StorageCredentials:
    """
    OAuth credentials for cloud storage providers.
    
    Attributes:
        access_token: OAuth access token
        refresh_token: OAuth refresh token (for long-lived access)
        token_expiry: When the access token expires
        scopes: List of OAuth scopes granted
        client_id: OAuth client ID (for refresh)
        client_secret: OAuth client secret (for refresh)
        token_uri: Token endpoint URI (for refresh)
        extra: Provider-specific credential data
    """
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    scopes: List[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_uri: Optional[str] = None
    extra: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []
        if self.extra is None:
            self.extra = {}
    
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if self.token_expiry is None:
            return False
        return datetime.utcnow() >= self.token_expiry


class CloudStorageProvider(ABC):
    """
    Abstract base class for cloud storage providers.
    
    All concrete providers (Google Drive, SharePoint, Dropbox) must implement
    this interface to ensure consistent behavior across the application.
    
    Usage:
        # Implementing a new provider
        class DropboxProvider(CloudStorageProvider):
            def authenticate(self, credentials):
                # Dropbox-specific auth
                pass
            
            def list_files(self, folder_id=None):
                # Dropbox-specific listing
                pass
    """
    
    def __init__(self, credentials: Optional[StorageCredentials] = None):
        """
        Initialize the storage provider.
        
        Args:
            credentials: OAuth credentials for authentication
        """
        self.credentials = credentials
        self._authenticated = False
        self.provider_name = self.__class__.__name__
    
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """
        Return the provider type identifier.
        
        Returns:
            str: Provider type (e.g., 'google_drive', 'sharepoint', 'dropbox')
        """
        pass
    
    @abstractmethod
    def authenticate(self, credentials: StorageCredentials) -> bool:
        """
        Authenticate with the storage provider.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            bool: True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    def refresh_credentials(self) -> StorageCredentials:
        """
        Refresh expired OAuth tokens.
        
        Returns:
            StorageCredentials: New credentials with refreshed tokens
            
        Raises:
            AuthenticationError: If refresh fails
        """
        pass
    
    @abstractmethod
    def list_files(
        self,
        folder_id: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 100,
        file_types: Optional[List[str]] = None
    ) -> List[FileMetadata]:
        """
        List files in a folder or matching a query.
        
        Args:
            folder_id: Folder ID to list files from (None = root)
            query: Search query string
            page_size: Maximum number of files to return
            file_types: Filter by MIME types (e.g., ['application/pdf'])
            
        Returns:
            List[FileMetadata]: List of file metadata
            
        Raises:
            StorageError: If listing fails
        """
        pass
    
    @abstractmethod
    def get_file_metadata(self, file_id: str) -> FileMetadata:
        """
        Get metadata for a specific file.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            FileMetadata: File metadata
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def download_file(self, file_id: str) -> bytes:
        """
        Download file content.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            bytes: File content as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If download fails
        """
        pass
    
    @abstractmethod
    def download_file_stream(self, file_id: str) -> BinaryIO:
        """
        Download file as a stream (for large files).
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            BinaryIO: File content stream
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If download fails
        """
        pass
    
    def is_authenticated(self) -> bool:
        """
        Check if provider is authenticated.
        
        Returns:
            bool: True if authenticated
        """
        return self._authenticated and self.credentials is not None
    
    def validate_credentials(self) -> bool:
        """
        Validate that credentials are valid and not expired.
        
        Returns:
            bool: True if credentials are valid
        """
        if not self.credentials:
            return False
        
        if self.credentials.is_expired():
            logger.info(f"{self.provider_name}: Access token expired, refreshing...")
            try:
                self.credentials = self.refresh_credentials()
                return True
            except Exception as e:
                logger.error(f"{self.provider_name}: Failed to refresh credentials: {e}")
                return False
        
        return True


class StorageError(Exception):
    """Base exception for storage provider errors."""
    pass


class AuthenticationError(StorageError):
    """Exception raised when authentication fails."""
    pass


class FileNotFoundError(StorageError):
    """Exception raised when a file is not found."""
    pass


class QuotaExceededError(StorageError):
    """Exception raised when storage quota is exceeded."""
    pass
