"""
OAuth Callback Endpoints.

Handles OAuth 2.0 redirect callbacks from cloud storage providers.
These endpoints are PUBLIC (no API key required) as they're called by external services.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth", tags=["oauth"])


@router.get("/callback")
async def oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    OAuth 2.0 callback endpoint.
    
    This endpoint receives the authorization code from OAuth providers
    (Google Drive, Microsoft Graph, etc.) after user authorization.
    
    Args:
        code: Authorization code from OAuth provider
        state: State parameter for CSRF protection
        error: Error message if authorization failed
        
    Returns:
        HTML page with the authorization code for the user to copy
    """
    logger.info(f"OAuth callback received: code={code[:20] if code else None}, state={state}, error={error}")
    
    if error:
        logger.error(f"OAuth authorization failed: {error}")
        return HTMLResponse(
            content=f"""
            <html>
                <head>
                    <title>OAuth Authorization Failed</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            max-width: 600px;
                            margin: 50px auto;
                            padding: 20px;
                            background-color: #f5f5f5;
                        }}
                        .error {{
                            background-color: #fee;
                            border: 1px solid #fcc;
                            border-radius: 5px;
                            padding: 20px;
                            color: #c33;
                        }}
                        h1 {{
                            color: #c33;
                            margin-top: 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="error">
                        <h1>❌ Authorization Failed</h1>
                        <p><strong>Error:</strong> {error}</p>
                        <p>Please try again or contact support if the problem persists.</p>
                    </div>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code:
        logger.error("OAuth callback missing authorization code")
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Return success page with code for user to copy
    return HTMLResponse(
        content=f"""
        <html>
            <head>
                <title>OAuth Authorization Successful</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 50px auto;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    .success {{
                        background-color: #efe;
                        border: 1px solid #cfc;
                        border-radius: 5px;
                        padding: 20px;
                    }}
                    h1 {{
                        color: #3c3;
                        margin-top: 0;
                    }}
                    .code-box {{
                        background-color: #fff;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        padding: 15px;
                        margin: 15px 0;
                        font-family: monospace;
                        word-break: break-all;
                        font-size: 14px;
                    }}
                    button {{
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 20px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 16px;
                    }}
                    button:hover {{
                        background-color: #45a049;
                    }}
                    .instructions {{
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #fff;
                        border-radius: 3px;
                        border-left: 4px solid #2196F3;
                    }}
                </style>
                <script>
                    function copyCode() {{
                        const code = document.getElementById('auth-code').textContent;
                        navigator.clipboard.writeText(code).then(() => {{
                            const btn = document.getElementById('copy-btn');
                            btn.textContent = '✓ Copied!';
                            setTimeout(() => {{
                                btn.textContent = 'Copy Code';
                            }}, 2000);
                        }});
                    }}
                </script>
            </head>
            <body>
                <div class="success">
                    <h1>✅ Authorization Successful!</h1>
                    <p>Your authorization code is:</p>
                    <div class="code-box" id="auth-code">{code}</div>
                    <button id="copy-btn" onclick="copyCode()">Copy Code</button>
                    
                    <div class="instructions">
                        <h3>Next Steps:</h3>
                        <ol>
                            <li>Click "Copy Code" above</li>
                            <li>Return to your terminal</li>
                            <li>Paste the code when prompted</li>
                        </ol>
                        <p><strong>Note:</strong> You can close this window after copying the code.</p>
                    </div>
                </div>
            </body>
        </html>
        """
    )


@router.get("/callback/google")
async def google_oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Google Drive OAuth callback (alias for main callback).
    
    Some implementations may use provider-specific callback URLs.
    """
    return await oauth_callback(request, code, state, error)


@router.get("/callback/microsoft")
async def microsoft_oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Microsoft Graph/SharePoint OAuth callback (alias for main callback).
    """
    return await oauth_callback(request, code, state, error)
