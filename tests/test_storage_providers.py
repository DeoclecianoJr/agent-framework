"""
Tests for Cloud Storage Providers (Story 7.3).

Tests:
- Abstract base class enforcement
- OAuth flow (authorization URL, code exchange, token refresh)
- Google Drive provider operations
- Provider factory
- Credential management
"""

import pytest
import json
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from io import BytesIO

from ai_framework.core.storage.base import (
    CloudStorageProvider,
    FileMetadata,
    StorageCredentials,
    StorageError,
    AuthenticationError,
    FileNotFoundError as StorageFileNotFoundError
)
from ai_framework.core.storage.oauth import OAuthManager, OAuthConfig
from ai_framework.core.storage.google_drive import GoogleDriveProvider
from ai_framework.core.storage.factory import StorageProviderFactory


# ==================== Fixtures ====================

@pytest.fixture
def mock_oauth_config():
    """Create mock OAuth config."""
    return OAuthConfig(
        client_id='test-client-id',
        client_secret='test-client-secret',
        redirect_uri='http://localhost:8000/callback',
        auth_url='https://accounts.google.com/o/oauth2/auth',
        token_url='https://oauth2.googleapis.com/token',
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )


@pytest.fixture
def mock_credentials():
    """Create mock storage credentials."""
    return StorageCredentials(
        access_token='test-access-token',
        refresh_token='test-refresh-token',
        token_expiry=datetime.utcnow() + timedelta(hours=1),
        scopes=['https://www.googleapis.com/auth/drive.readonly'],
        extra={
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret'
        }
    )


@pytest.fixture
def mock_expired_credentials():
    """Create mock expired credentials."""
    return StorageCredentials(
        access_token='test-access-token',
        refresh_token='test-refresh-token',
        token_expiry=datetime.utcnow() - timedelta(hours=1),
        scopes=['https://www.googleapis.com/auth/drive.readonly'],
        extra={
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret'
        }
    )


# ==================== Abstract Base Class Tests ====================

class TestAbstractBaseClass:
    """Test abstract base class enforcement."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Cannot instantiate CloudStorageProvider directly."""
        with pytest.raises(TypeError):
            CloudStorageProvider()
    
    def test_subclass_must_implement_abstract_methods(self):
        """Subclass must implement all abstract methods."""
        class IncompleteProvider(CloudStorageProvider):
            @property
            def provider_type(self):
                return "incomplete"
        
        with pytest.raises(TypeError):
            IncompleteProvider()


# ==================== OAuth Manager Tests ====================

class TestOAuthManager:
    """Test OAuth 2.0 manager."""
    
    def test_create_google_drive_config(self):
        """Can create Google Drive OAuth config."""
        config = OAuthManager.create_google_drive_config(
            client_id='test-id',
            client_secret='test-secret',
            redirect_uri='http://localhost/callback'
        )
        
        assert config.client_id == 'test-id'
        assert config.client_secret == 'test-secret'
        assert config.redirect_uri == 'http://localhost/callback'
        assert 'drive.readonly' in config.scopes[0]
    
    def test_get_authorization_url(self, mock_oauth_config):
        """Can generate authorization URL."""
        manager = OAuthManager(mock_oauth_config)
        url, state = manager.get_authorization_url()
        
        assert 'accounts.google.com' in url
        assert 'client_id=test-client-id' in url
        assert 'redirect_uri=' in url
        assert f'state={state}' in url
        assert len(state) == 32  # Security token
    
    @patch('requests.post')
    def test_exchange_code_success(self, mock_post, mock_oauth_config):
        """Can exchange authorization code for tokens."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new-access-token',
            'refresh_token': 'new-refresh-token',
            'expires_in': 3600,
            'scope': 'https://www.googleapis.com/auth/drive.readonly'
        }
        mock_post.return_value = mock_response
        
        manager = OAuthManager(mock_oauth_config)
        credentials = manager.exchange_code('test-code')
        
        assert credentials.access_token == 'new-access-token'
        assert credentials.refresh_token == 'new-refresh-token'
        assert not credentials.is_expired()
    
    @patch('requests.post')
    def test_exchange_code_failure(self, mock_post, mock_oauth_config):
        """Raises error on failed code exchange."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid authorization code'
        mock_response.raise_for_status.side_effect = requests.RequestException('Bad Request')
        mock_post.return_value = mock_response
        
        manager = OAuthManager(mock_oauth_config)
        
        with pytest.raises(AuthenticationError):
            manager.exchange_code('invalid-code')
    
    @patch('requests.post')
    def test_refresh_token_success(self, mock_post, mock_oauth_config, mock_expired_credentials):
        """Can refresh expired tokens."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'refreshed-access-token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        manager = OAuthManager(mock_oauth_config)
        new_credentials = manager.refresh_token(mock_expired_credentials)
        
        assert new_credentials.access_token == 'refreshed-access-token'
        assert not new_credentials.is_expired()
    
    def test_serialize_deserialize_credentials(self, mock_credentials):
        """Can serialize and deserialize credentials."""
        serialized = OAuthManager.serialize_credentials(mock_credentials)
        assert isinstance(serialized, str)
        
        deserialized = OAuthManager.deserialize_credentials(serialized)
        assert deserialized.access_token == mock_credentials.access_token
        assert deserialized.refresh_token == mock_credentials.refresh_token


# ==================== StorageCredentials Tests ====================

class TestStorageCredentials:
    """Test StorageCredentials dataclass."""
    
    def test_is_expired_with_valid_token(self, mock_credentials):
        """Valid token is not expired."""
        assert not mock_credentials.is_expired()
    
    def test_is_expired_with_expired_token(self, mock_expired_credentials):
        """Expired token is detected."""
        assert mock_expired_credentials.is_expired()
    
    def test_is_expired_without_expiry(self):
        """Token without expiry is not expired."""
        creds = StorageCredentials(
            access_token='test',
            refresh_token='test',
            token_expiry=None,
            scopes=[]
        )
        assert not creds.is_expired()


# ==================== Google Drive Provider Tests ====================

class TestGoogleDriveProvider:
    """Test Google Drive provider implementation."""
    
    def test_provider_type(self):
        """Provider type is 'google_drive'."""
        provider = GoogleDriveProvider()
        assert provider.provider_type == 'google_drive'
    
    @patch('ai_framework.core.storage.google_drive.build')
    def test_authenticate_success(self, mock_build, mock_credentials):
        """Can authenticate with valid credentials."""
        # Mock Google Drive service
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {'files': []}
        mock_build.return_value = mock_service
        
        provider = GoogleDriveProvider()
        result = provider.authenticate(mock_credentials)
        
        assert result is True
        assert provider.is_authenticated()
    
    @patch('ai_framework.core.storage.google_drive.build')
    def test_authenticate_failure(self, mock_build, mock_credentials):
        """Raises error on authentication failure."""
        mock_build.side_effect = Exception("Authentication failed")
        
        provider = GoogleDriveProvider()
        
        with pytest.raises(AuthenticationError):
            provider.authenticate(mock_credentials)
    
    @patch('ai_framework.core.storage.google_drive.build')
    def test_list_files(self, mock_build, mock_credentials):
        """Can list files from Google Drive."""
        # Mock file data
        mock_files = [
            {
                'id': 'file1',
                'name': 'document.pdf',
                'mimeType': 'application/pdf',
                'size': '1024',
                'modifiedTime': '2024-01-15T10:00:00Z',
                'createdTime': '2024-01-01T10:00:00Z',
                'webViewLink': 'https://drive.google.com/file/d/file1',
                'parents': ['folder1']
            },
            {
                'id': 'folder1',
                'name': 'My Folder',
                'mimeType': 'application/vnd.google-apps.folder',
                'modifiedTime': '2024-01-10T10:00:00Z',
                'createdTime': '2024-01-01T10:00:00Z'
            }
        ]
        
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {'files': mock_files}
        mock_build.return_value = mock_service
        
        provider = GoogleDriveProvider(mock_credentials)
        provider.authenticate(mock_credentials)
        
        files = provider.list_files()
        
        assert len(files) == 2
        assert files[0].id == 'file1'
        assert files[0].name == 'document.pdf'
        assert files[1].is_folder is True
    
    @patch('ai_framework.core.storage.google_drive.build')
    def test_get_file_metadata(self, mock_build, mock_credentials):
        """Can get file metadata."""
        mock_file = {
            'id': 'file1',
            'name': 'document.pdf',
            'mimeType': 'application/pdf',
            'size': '2048',
            'modifiedTime': '2024-01-15T10:00:00Z',
            'createdTime': '2024-01-01T10:00:00Z',
            'webViewLink': 'https://drive.google.com/file/d/file1'
        }
        
        mock_service = MagicMock()
        mock_service.files().get().execute.return_value = mock_file
        mock_build.return_value = mock_service
        
        provider = GoogleDriveProvider(mock_credentials)
        provider.authenticate(mock_credentials)
        
        metadata = provider.get_file_metadata('file1')
        
        assert metadata.id == 'file1'
        assert metadata.name == 'document.pdf'
        assert metadata.size == 2048
    
    @patch('ai_framework.core.storage.google_drive.build')
    def test_download_file(self, mock_build, mock_credentials):
        """Can download file content."""
        mock_content = b'PDF file content here'
        
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_service.files().get_media.return_value = mock_request
        mock_build.return_value = mock_service
        
        # Mock MediaIoBaseDownload
        with patch('ai_framework.core.storage.google_drive.MediaIoBaseDownload') as mock_download:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.return_value = (None, True)
            mock_download.return_value = mock_downloader
            
            provider = GoogleDriveProvider(mock_credentials)
            provider.authenticate(mock_credentials)
            
            # Manually set buffer content for test
            with patch('io.BytesIO') as mock_buffer:
                buffer_instance = BytesIO(mock_content)
                mock_buffer.return_value = buffer_instance
                
                content = provider.download_file('file1')
                
                assert isinstance(content, bytes)


# ==================== Provider Factory Tests ====================

class TestStorageProviderFactory:
    """Test storage provider factory."""
    
    def test_get_available_providers(self):
        """Can get list of available providers."""
        providers = StorageProviderFactory.get_available_providers()
        assert 'google_drive' in providers
    
    def test_create_google_drive_provider(self, mock_credentials):
        """Can create Google Drive provider."""
        with patch('ai_framework.core.storage.google_drive.build'):
            provider = StorageProviderFactory.create_provider(
                'google_drive',
                mock_credentials,
                auto_authenticate=False
            )
            
            assert isinstance(provider, GoogleDriveProvider)
            assert provider.provider_type == 'google_drive'
    
    def test_create_unknown_provider(self):
        """Raises error for unknown provider type."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            StorageProviderFactory.create_provider('unknown_provider')
    
    def test_register_new_provider(self):
        """Can register new provider type."""
        class CustomProvider(CloudStorageProvider):
            @property
            def provider_type(self):
                return "custom"
            
            def authenticate(self, credentials):
                return True
            
            def refresh_credentials(self):
                return self.credentials
            
            def list_files(self, **kwargs):
                return []
            
            def get_file_metadata(self, file_id):
                return None
            
            def download_file(self, file_id):
                return b''
            
            def download_file_stream(self, file_id):
                return BytesIO()
        
        StorageProviderFactory.register_provider('custom', CustomProvider)
        
        providers = StorageProviderFactory.get_available_providers()
        assert 'custom' in providers
        
        provider = StorageProviderFactory.create_provider('custom', auto_authenticate=False)
        assert isinstance(provider, CustomProvider)


# ==================== Integration Tests ====================

class TestStorageIntegration:
    """Integration tests for storage system."""
    
    @patch('ai_framework.core.storage.google_drive.build')
    @patch('requests.post')
    def test_complete_oauth_flow(self, mock_post, mock_build):
        """Test complete OAuth flow from authorization to file listing."""
        # Mock token exchange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': 'https://www.googleapis.com/auth/drive.readonly'
        }
        mock_post.return_value = mock_response
        
        # Mock Drive service
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {'files': []}
        mock_build.return_value = mock_service
        
        # 1. Create OAuth manager
        config = OAuthManager.create_google_drive_config(
            'test-id', 'test-secret', 'http://localhost/callback'
        )
        oauth = OAuthManager(config)
        
        # 2. Get authorization URL
        url, state = oauth.get_authorization_url()
        assert 'accounts.google.com' in url
        
        # 3. Exchange code for credentials
        credentials = oauth.exchange_code('auth-code')
        assert credentials.access_token == 'new-token'
        
        # 4. Create provider with credentials
        provider = StorageProviderFactory.create_provider(
            'google_drive',
            credentials,
            auto_authenticate=True
        )
        
        # 5. List files
        files = provider.list_files()
        assert isinstance(files, list)
