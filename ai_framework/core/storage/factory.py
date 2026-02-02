"""
Storage Provider Factory.

Creates and manages cloud storage provider instances.

Story 7.3: Google Drive OAuth 2.0 Integration
"""

import logging
from typing import Dict, Type, Optional
from sqlalchemy.orm import Session

from .base import CloudStorageProvider, StorageCredentials
from .google_drive import GoogleDriveProvider
from .oauth import OAuthManager

logger = logging.getLogger(__name__)


class StorageProviderFactory:
    """
    Factory for creating cloud storage provider instances.
    
    Features:
    - Provider registration system
    - Automatic authentication
    - Credential management from database
    - Support for multiple providers
    
    Usage:
        # Register providers (done automatically)
        factory = StorageProviderFactory()
        
        # Create provider from knowledge_source
        source = db.query(KnowledgeSource).filter_by(id=source_id).first()
        provider = factory.create_provider(source.source_type, source.credentials)
        
        # Or create with raw credentials
        credentials = StorageCredentials(...)
        drive = factory.create_provider('google_drive', credentials)
    """
    
    # Registry of provider types
    _providers: Dict[str, Type[CloudStorageProvider]] = {}
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[CloudStorageProvider]):
        """
        Register a storage provider.
        
        Args:
            provider_type: Provider identifier (e.g., 'google_drive')
            provider_class: Provider class
        """
        cls._providers[provider_type] = provider_class
        logger.info(f"Registered storage provider: {provider_type}")
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """
        Get list of available provider types.
        
        Returns:
            list[str]: List of provider type identifiers
        """
        return list(cls._providers.keys())
    
    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        credentials: Optional[StorageCredentials] = None,
        auto_authenticate: bool = True
    ) -> CloudStorageProvider:
        """
        Create a storage provider instance.
        
        Args:
            provider_type: Provider type ('google_drive', 'sharepoint', etc.)
            credentials: OAuth credentials
            auto_authenticate: Automatically authenticate provider
            
        Returns:
            CloudStorageProvider: Initialized provider instance
            
        Raises:
            ValueError: If provider type is unknown
            AuthenticationError: If authentication fails
        """
        if provider_type not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider type '{provider_type}'. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._providers[provider_type]
        provider = provider_class(credentials)
        
        if auto_authenticate and credentials:
            provider.authenticate(credentials)
        
        logger.info(f"Created provider: {provider_type}")
        return provider
    
    @classmethod
    def create_from_knowledge_source(
        cls,
        db: Session,
        source_id: str,
        auto_authenticate: bool = True
    ) -> CloudStorageProvider:
        """
        Create provider from KnowledgeSource model.
        
        Args:
            db: Database session
            source_id: KnowledgeSource ID
            auto_authenticate: Automatically authenticate
            
        Returns:
            CloudStorageProvider: Initialized provider
            
        Raises:
            ValueError: If source not found
            AuthenticationError: If authentication fails
        """
        from app.core.models import KnowledgeSource
        
        source = db.query(KnowledgeSource).filter_by(id=source_id).first()
        if not source:
            raise ValueError(f"KnowledgeSource {source_id} not found")
        
        # Deserialize credentials from config
        from .oauth import OAuthManager
        creds_json = source.config.get('credentials')
        if not creds_json:
            raise ValueError(f"No credentials found in source {source_id} config")
        
        credentials = OAuthManager.deserialize_credentials(creds_json)
        
        # Create provider
        provider = cls.create_provider(
            provider_type=source.source_type,
            credentials=credentials,
            auto_authenticate=auto_authenticate
        )
        
        # Check if credentials need refresh
        if auto_authenticate and credentials.is_expired():
            logger.info(f"Refreshing expired credentials for source {source_id}")
            new_credentials = provider.refresh_credentials()
            
            # Update database with new credentials
            source.config['credentials'] = OAuthManager.serialize_credentials(new_credentials)
            db.commit()
        
        return provider


# Register built-in providers
StorageProviderFactory.register_provider('google_drive', GoogleDriveProvider)

# Future providers will be registered here:
# StorageProviderFactory.register_provider('sharepoint', SharePointProvider)
# StorageProviderFactory.register_provider('dropbox', DropboxProvider)
