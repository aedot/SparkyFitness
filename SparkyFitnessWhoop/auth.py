"""
Authentication routes for Whoop OAuth flow
"""

import logging
import time
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from config import settings
from services.whoop_client import WhoopOAuthClient, WhoopClient

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth client
oauth_client = WhoopOAuthClient(
    client_id=settings.WHOOP_CLIENT_ID,
    client_secret=settings.WHOOP_CLIENT_SECRET,
    redirect_uri=settings.WHOOP_REDIRECT_URI,
    oauth_url=settings.WHOOP_OAUTH_URL
)

# In-memory token store (replace with database in production)
TOKEN_STORE: dict = {}


@router.get("/login")
async def whoop_login(user_id: str = Query(..., description="SparkyFitness user ID")):
    """
    Initiate Whoop OAuth login flow
    
    Redirects user to Whoop consent screen where they authorize the app.
    After authorization, Whoop redirects to /callback with authorization code.
    
    Args:
        user_id: SparkyFitness user ID (passed as state parameter)
    
    Returns:
        RedirectResponse to Whoop OAuth authorization URL
    """
    try:
        logger.info(f"Initiating Whoop login for user: {user_id}")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id parameter required")
        
        # Generate authorization URL
        auth_url = oauth_client.get_authorization_url(state=user_id)
        
        # Redirect user to Whoop
        return RedirectResponse(url=auth_url)
    
    except Exception as e:
        logger.error(f"Error initiating login: {e}")
        raise HTTPException(status_code=500, detail=f"Login initiation failed: {str(e)}")


@router.get("/callback")
async def whoop_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle Whoop OAuth callback
    
    Whoop redirects here after user authorizes the app.
    Exchanges authorization code for access and refresh tokens.
    
    Args:
        code: Authorization code from Whoop
        state: State parameter (should be user_id)
    
    Returns:
        JSON with success status and access token
    """
    user_id = state
    
    try:
        logger.info(f"Handling Whoop callback for user: {user_id}")
        
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or state parameter")
        
        # Exchange authorization code for tokens
        tokens = oauth_client.exchange_code_for_token(code)
        
        # Store tokens (in production, use secure database)
        TOKEN_STORE[user_id] = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": time.time() + tokens.get("expires_in", 86400),
            "created_at": time.time()
        }
        
        logger.info(f"Successfully authenticated user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "access_token": tokens.get("access_token"),
            "message": "Successfully connected to Whoop! You can now close this window."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/disconnect")
async def whoop_disconnect(user_id: str = Query(..., description="SparkyFitness user ID")):
    """
    Disconnect Whoop integration for a user
    
    Removes stored tokens for the user.
    
    Args:
        user_id: SparkyFitness user ID
    
    Returns:
        JSON with disconnection status
    """
    try:
        logger.info(f"Disconnecting Whoop for user: {user_id}")
        
        if user_id in TOKEN_STORE:
            del TOKEN_STORE[user_id]
            logger.info(f"Successfully disconnected user {user_id}")
            return {"status": "disconnected", "user_id": user_id}
        else:
            raise HTTPException(status_code=404, detail="User not connected")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting: {e}")
        raise HTTPException(status_code=500, detail=f"Disconnection failed: {str(e)}")


@router.get("/status/{user_id}")
async def check_connection_status(user_id: str):
    """
    Check if a user is connected to Whoop
    
    Args:
        user_id: SparkyFitness user ID
    
    Returns:
        JSON with connection status
    """
    is_connected = user_id in TOKEN_STORE
    
    if is_connected:
        tokens = TOKEN_STORE[user_id]
        expires_at = tokens.get("expires_at", 0)
        is_expired = time.time() > expires_at
        
        return {
            "user_id": user_id,
            "connected": True,
            "token_expired": is_expired,
            "expires_at": expires_at
        }
    else:
        return {
            "user_id": user_id,
            "connected": False
        }


def get_user_token(user_id: str) -> str:
    """
    Retrieve stored access token for a user
    
    Raises HTTPException if token not found or expired
    """
    if user_id not in TOKEN_STORE:
        logger.warning(f"No token found for user {user_id}")
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    tokens = TOKEN_STORE[user_id]
    
    # Check if token is expired
    expires_at = tokens.get("expires_at", 0)
    if time.time() > expires_at:
        logger.warning(f"Token expired for user {user_id}")
        
        # Try to refresh token
        refresh_token = tokens.get("refresh_token")
        if refresh_token:
            try:
                logger.info(f"Attempting to refresh token for user {user_id}")
                new_tokens = oauth_client.refresh_token(refresh_token)
                
                # Update stored token
                TOKEN_STORE[user_id]["access_token"] = new_tokens.get("access_token")
                TOKEN_STORE[user_id]["expires_at"] = time.time() + new_tokens.get("expires_in", 86400)
                
                logger.info(f"Successfully refreshed token for user {user_id}")
                return new_tokens.get("access_token")
            
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise HTTPException(status_code=401, detail="Token refresh failed")
        else:
            raise HTTPException(status_code=401, detail="Token expired and no refresh token available")
    
    return tokens.get("access_token")