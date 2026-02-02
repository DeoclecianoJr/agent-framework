"""
Generic OAuth 2.0 Manager for Cloud Storage Providers.

Handles OAuth flow, token refresh, and credential management
for Google Drive, SharePoint, Dropbox, and other providers.

Story 7.3: Cloud Storage Integration - OAuth System
"""

import os
import json
import logging
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests

from .base import StorageCredentials, AuthenticationError

logger = logging.getLogger(__name__)


class OAuthConfig:
    """OAuth configuration for a provider."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        auth_url: str,
        token_url: str,
        scopes: List[str],
        provider_name: str = "generic"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = auth_url
        self.token_url = token_url
        self.scopes = scopes
        self.provider_name = provider_name
    
    @property
    def token_uri(self) -> str:
        """Alias for token_url (for compatibility with Google API)."""
        return self.token_url


class OAuthManager:
    """
    Generic OAuth 2.0 manager supporting multiple providers.
    
    Handles:
    - Authorization URL generation
    - Token exchange from authorization code
    - Token refresh
    - Credential serialization/deserialization
    
    Usage:
        # Google Drive
        config = OAuthConfig(
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            redirect_uri='http://localhost:8000/oauth/callback',
            auth_url='https://accounts.google.com/o/oauth2/v2/auth',
            token_url='https://oauth2.googleapis.com/token',
            scopes=['https://www.googleapis.com/auth/drive.readonly'],
            provider_name='google_drive'
        )
        
        oauth = OAuthManager(config)
        
        # Step 1: Get authorization URL
        auth_url = oauth.get_authorization_url()
        # Redirect user to auth_url
        
        # Step 2: Exchange code for tokens
        credentials = oauth.exchange_code(authorization_code)
        
        # Step 3: Refresh when needed
        new_credentials = oauth.refresh_token(credentials)
    """
    
    def __init__(self, config: OAuthConfig):
        """
        Initialize OAuth manager.
        
        Args:
            config: OAuth configuration for the provider
        """
        self.config = config
    
    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection (auto-generated if None)
            
        Returns:
            tuple[str, str]: Authorization URL and state token
        """
        # Generate CSRF token if not provided
        if not state:
            state = secrets.token_hex(16)
        
        params = {
            'client_id': self.config.client_id,
            'redirect_uri': self.config.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.config.scopes),
            'access_type': 'offline',  # Request refresh token
            'prompt': 'consent',  # Force consent to get refresh token
            'state': state
        }
        
        auth_url = f"{self.config.auth_url}?{urlencode(params)}"
        logger.info(f"{self.config.provider_name}: Generated authorization URL")
        return auth_url, state
    
    def exchange_code(self, authorization_code: str) -> StorageCredentials:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Code received from OAuth callback
            
        Returns:
            StorageCredentials: OAuth credentials
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'code': authorization_code,
            'redirect_uri': self.config.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(self.config.token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            credentials = self._parse_token_response(token_data)
            logger.info(f"{self.config.provider_name}: Successfully exchanged code for tokens")
            return credentials
            
        except requests.RequestException as e:
            logger.error(f"{self.config.provider_name}: Token exchange failed: {e}")
            raise AuthenticationError(f"Failed to exchange authorization code: {e}")
    
    def refresh_token(self, credentials: StorageCredentials) -> StorageCredentials:
        """
        Refresh access token using refresh token.
        
        Args:
            credentials: Current credentials with refresh token
            
        Returns:
            StorageCredentials: New credentials with fresh access token
            
        Raises:
            AuthenticationError: If refresh fails
        """
        if not credentials.refresh_token:
            raise AuthenticationError("No refresh token available")
        
        data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'refresh_token': credentials.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(self.config.token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            new_credentials = self._parse_token_response(token_data)
            
            # Preserve refresh token if not returned (some providers don't return it)
            if not new_credentials.refresh_token:
                new_credentials.refresh_token = credentials.refresh_token
            
            logger.info(f"{self.config.provider_name}: Successfully refreshed access token")
            return new_credentials
            
        except requests.RequestException as e:
            logger.error(f"{self.config.provider_name}: Token refresh failed: {e}")
            raise AuthenticationError(f"Failed to refresh token: {e}")
    
    def _parse_token_response(self, token_data: Dict[str, Any]) -> StorageCredentials:
        """
        Parse token response into StorageCredentials.
        
        Args:
            token_data: Response data from token endpoint
            
        Returns:
            StorageCredentials: Parsed credentials
        """
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in')
        scope = token_data.get('scope', '')
        
        # Calculate token expiry
        token_expiry = None
        if expires_in:
            token_expiry = datetime.utcnow() + timedelta(seconds=int(expires_in))
        
        # Parse scopes
        scopes = scope.split() if scope else self.config.scopes
        
        return StorageCredentials(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            scopes=scopes,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            token_uri=self.config.token_url,
            extra=token_data  # Store full response for provider-specific data
        )
    
    @staticmethod
    def serialize_credentials(credentials: StorageCredentials) -> str:
        """
        Serialize credentials to JSON for storage.
        
        Args:
            credentials: Credentials to serialize
            
        Returns:
            str: JSON string
        """
        data = {
            'access_token': credentials.access_token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': credentials.token_expiry.isoformat() if credentials.token_expiry else None,
            'scopes': credentials.scopes,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'token_uri': credentials.token_uri,
            'extra': credentials.extra
        }
        return json.dumps(data)
    
    @staticmethod
    def deserialize_credentials(json_str: str) -> StorageCredentials:
        """
        Deserialize credentials from JSON.
        
        Args:
            json_str: JSON string with credentials
            
        Returns:
            StorageCredentials: Deserialized credentials
        """
        data = json.loads(json_str)
        
        token_expiry = None
        if data.get('token_expiry'):
            token_expiry = datetime.fromisoformat(data['token_expiry'])
        
        return StorageCredentials(
            access_token=data['access_token'],
            refresh_token=data.get('refresh_token'),
            token_expiry=token_expiry,
            scopes=data.get('scopes', []),
            client_id=data.get('client_id'),
            client_secret=data.get('client_secret'),
            token_uri=data.get('token_uri'),
            extra=data.get('extra', {})
        )
    
    @staticmethod
    def create_google_drive_config(
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> OAuthConfig:
        """
        Create OAuth config for Google Drive.
        
        Args:
            client_id: Google OAuth client ID (from env if None)
            client_secret: Google OAuth client secret (from env if None)
            redirect_uri: OAuth redirect URI (from env if None)
        
        Returns:
            OAuthConfig: Google Drive OAuth configuration
            
        Raises:
            ValueError: If required parameters are missing
        """
        client_id = client_id or os.getenv('GOOGLE_CLIENT_ID')
        client_secret = client_secret or os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = redirect_uri or os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/oauth/google/callback')
        
        if not client_id or not client_secret:
            raise ValueError(
                "client_id and client_secret must be provided or set in environment (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)"
            )
        
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            auth_url='https://accounts.google.com/o/oauth2/v2/auth',
            token_url='https://oauth2.googleapis.com/token',
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/drive.metadata.readonly'
            ],
            provider_name='google_drive'
        )
    
    @staticmethod
    @staticmethod
    def create_sharepoint_config(
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> OAuthConfig:
        """
        Create OAuth config for SharePoint/Microsoft Graph.
        
        Args:
            client_id: Microsoft OAuth client ID (from env if None)
            client_secret: Microsoft OAuth client secret (from env if None)
            tenant_id: Microsoft tenant ID (from env if None)
            redirect_uri: OAuth redirect URI (from env if None)
        
        Returns:
            OAuthConfig: SharePoint OAuth configuration
            
        Raises:
            ValueError: If required parameters are missing
        """
        client_id = client_id or os.getenv('MICROSOFT_CLIENT_ID')
        client_secret = client_secret or os.getenv('MICROSOFT_CLIENT_SECRET')
        tenant_id = tenant_id or os.getenv('MICROSOFT_TENANT_ID', 'common')
        redirect_uri = redirect_uri or os.getenv('MICROSOFT_REDIRECT_URI', 'http://localhost:8000/oauth/microsoft/callback')
        
        if not client_id or not client_secret:
            raise ValueError(
                "client_id and client_secret must be provided or set in environment (MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET)"
            )
        
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            auth_url=f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize',
            token_url=f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
            scopes=[
                'https://graph.microsoft.com/Files.Read.All',
                'https://graph.microsoft.com/Sites.Read.All',
                'offline_access'
            ],
            provider_name='sharepoint'
        )
