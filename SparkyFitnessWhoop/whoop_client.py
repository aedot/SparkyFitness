"""
Whoop API Client Service
Handles all API interactions with Whoop
"""

import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class WhoopAPIError(Exception):
    """Base exception for Whoop API errors"""
    pass

class WhoopClient:
    """
    Whoop API client wrapper
    Handles authentication and API calls
    """
    
    def __init__(self, access_token: str, base_url: str, timeout: int = 30):
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict:
        """
        Make HTTP request to Whoop API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/user/profile")
            params: Query parameters
            json_data: JSON body for POST requests
        
        Returns:
            Response JSON
        
        Raises:
            HTTPException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method.upper() == "GET":
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle different status codes
            if response.status_code == 401:
                logger.error("Unauthorized - access token expired or invalid")
                raise HTTPException(status_code=401, detail="Whoop authentication failed")
            
            if response.status_code == 403:
                logger.error("Forbidden - insufficient permissions")
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            if response.status_code == 429:
                logger.warning("Rate limited by Whoop API")
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            if response.status_code >= 500:
                logger.error(f"Whoop API server error: {response.status_code}")
                raise HTTPException(status_code=500, detail="Whoop API server error")
            
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout to {url}")
            raise HTTPException(status_code=504, detail="Whoop API timeout")
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {url}")
            raise HTTPException(status_code=503, detail="Whoop API unavailable")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")
    
    def get_user(self) -> Dict:
        """Get current user profile"""
        logger.info("Fetching user profile")
        return self._request("GET", "/user/profile")
    
    def get_cycles(self, start_date: str, end_date: str) -> Dict:
        """
        Get daily cycles with all metrics
        
        Args:
            start_date: Start date (YYYY-MM-DD or ISO format)
            end_date: End date (YYYY-MM-DD or ISO format)
        
        Returns:
            Cycles data with strain, recovery, sleep, HR
        """
        logger.info(f"Fetching cycles from {start_date} to {end_date}")
        
        params = {
            "start": start_date,
            "end": end_date
        }
        
        return self._request("GET", "/user/cycles", params=params)
    
    def get_recovery(self, start_date: str, end_date: str) -> Dict:
        """Get recovery data for date range"""
        logger.info(f"Fetching recovery data from {start_date} to {end_date}")
        
        params = {
            "start": start_date,
            "end": end_date
        }
        
        return self._request("GET", "/user/recovery", params=params)
    
    def get_sleep(self, start_date: str, end_date: str) -> Dict:
        """Get sleep data for date range"""
        logger.info(f"Fetching sleep data from {start_date} to {end_date}")
        
        params = {
            "start": start_date,
            "end": end_date
        }
        
        return self._request("GET", "/user/sleep", params=params)
    
    def get_workouts(self, start_date: str, end_date: str) -> Dict:
        """Get workout/activity data for date range"""
        logger.info(f"Fetching workouts from {start_date} to {end_date}")
        
        params = {
            "start": start_date,
            "end": end_date
        }
        
        return self._request("GET", "/user/activities", params=params)
    
    def validate_token(self) -> bool:
        """
        Validate that access token is still valid
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            self.get_user()
            logger.info("Access token is valid")
            return True
        except HTTPException as e:
            if e.status_code == 401:
                logger.warning("Access token is expired or invalid")
                return False
            raise


class WhoopOAuthClient:
    """
    Handles Whoop OAuth 2.0 token exchange
    """
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, oauth_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.oauth_url = oauth_url
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate Whoop OAuth authorization URL
        
        Args:
            state: State parameter (typically user_id)
        
        Returns:
            Authorization URL to redirect user to
        """
        scopes = "read:cycles_collection read:user offline"
        
        auth_url = (
            f"{self.oauth_url}/auth?"
            f"client_id={self.client_id}&"
            f"scope={scopes}&"
            f"response_type=code&"
            f"redirect_uri={self.redirect_uri}&"
            f"state={state}"
        )
        
        logger.info(f"Generated OAuth URL for state: {state}")
        return auth_url
    
    def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            code: Authorization code from Whoop
        
        Returns:
            Dict with access_token, refresh_token, expires_in
        
        Raises:
            HTTPException: If token exchange fails
        """
        token_url = f"{self.oauth_url}/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        try:
            logger.info("Exchanging authorization code for token")
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            tokens = response.json()
            logger.info("Successfully obtained tokens")
            return tokens
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            raise HTTPException(status_code=500, detail="Token exchange failed")
    
    def refresh_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token from previous login
        
        Returns:
            Dict with new access_token and expires_in
        
        Raises:
            HTTPException: If refresh fails
        """
        token_url = f"{self.oauth_url}/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            logger.info("Refreshing access token")
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            tokens = response.json()
            logger.info("Successfully refreshed token")
            return tokens
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(status_code=500, detail="Token refresh failed")