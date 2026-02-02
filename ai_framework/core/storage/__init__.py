"""
Cloud Storage Provider Package.

Provides abstracted cloud storage integration with OAuth 2.0 authentication.

Supported Providers:
- Google Drive (Story 7.3)
- SharePoint (Story 7.4 - planned)
- Dropbox (planned)
- Box (planned)

Usage:
    from ai_framework.core.storage import StorageProviderFactory, OAuthManager
    
    # Create OAuth config
    config = OAuthManager.create_google_drive_config(
        client_id='your-client-id',
        client_secret='your-client-secret',
        redirect_uri='http://localhost:8000/callback'
    )
    
    # Initialize OAuth manager
    oauth = OAuthManager(config)
    
    # Get authorization URL
    auth_url, state = oauth.get_authorization_url()
    # Redirect user to auth_url
    
    # After user authorizes, exchange code for credentials
    credentials = oauth.exchange_code(authorization_code)
    
    # Create provider
    provider = StorageProviderFactory.create_provider('google_drive', credentials)
    
    # Use provider
    files = provider.list_files()
    content = provider.download_file(file_id)
"""

from .base import (
    CloudStorageProvider,
    FileMetadata,
    StorageCredentials,
    StorageError,
    AuthenticationError,
    FileNotFoundError,
    QuotaExceededError,
)
from .oauth import OAuthManager, OAuthConfig
from .factory import StorageProviderFactory
from .google_drive import GoogleDriveProvider

__all__ = [
    "CloudStorageProvider",
    "FileMetadata",
    "StorageCredentials",
    "StorageError",
    "AuthenticationError",
    "FileNotFoundError",
    "QuotaExceededError",
    "OAuthManager",
    "OAuthConfig",
    "StorageProviderFactory",
    "GoogleDriveProvider",
]
