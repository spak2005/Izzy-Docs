"""
ChatGPT Authentication Middleware

Handles authentication for requests coming from ChatGPT via the OpenAI Apps SDK.
ChatGPT passes bearer tokens in Authorization headers that need to be validated
and converted to Google credentials for API access.
"""

import logging
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class ChatGPTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle ChatGPT bearer token authentication.

    ChatGPT sends OAuth access tokens in Authorization headers.
    This middleware:
    1. Extracts the bearer token from the Authorization header
    2. Validates the token against our OAuth session store
    3. Injects user context for downstream tool handlers
    """

    async def dispatch(self, request: Request, call_next):
        """Process the request, extracting and validating ChatGPT auth tokens."""
        # Only process requests with Authorization headers
        auth_header = request.headers.get("authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            logger.debug(f"ChatGPT auth: Bearer token received (length: {len(token)})")

            # Validate the token
            user_info = await self._validate_chatgpt_token(token)

            if user_info:
                # Store user info in request state for downstream handlers
                request.state.chatgpt_user = user_info
                request.state.chatgpt_authenticated = True
                request.state.authenticated_user_email = user_info.get("email")
                logger.info(f"ChatGPT auth: Authenticated user {user_info.get('email')}")
            else:
                logger.warning("ChatGPT auth: Token validation failed")
                request.state.chatgpt_authenticated = False

        response = await call_next(request)
        return response

    async def _validate_chatgpt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a bearer token from ChatGPT.

        The token could be:
        1. A Google access token (ya29.*) we issued during OAuth flow
        2. A JWT ID token
        3. A session token from our OAuth session store

        Args:
            token: The bearer token to validate

        Returns:
            User info dict if valid, None otherwise
        """
        try:
            from auth.oauth21_session_store import get_oauth21_session_store
            from auth.google_auth import get_user_info
            from google.oauth2.credentials import Credentials

            store = get_oauth21_session_store()

            # Check if it's a Google access token (ya29.*)
            if token.startswith("ya29."):
                logger.debug("ChatGPT auth: Validating Google access token")

                # Try to get user info from the token
                from auth.oauth_config import get_oauth_config
                config = get_oauth_config()

                creds = Credentials(
                    token=token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                )

                user_info = get_user_info(creds)
                if user_info and user_info.get("email"):
                    logger.debug(f"ChatGPT auth: Token valid for {user_info['email']}")
                    return user_info

            # Check if it matches a stored session
            session = store.get_session_by_access_token(token)
            if session:
                logger.debug("ChatGPT auth: Found session for token")
                return {
                    "email": session.get("user_email"),
                    "id": session.get("user_id"),
                }

            logger.debug("ChatGPT auth: Token not recognized")
            return None

        except Exception as e:
            logger.error(f"ChatGPT auth: Token validation error: {e}")
            return None


def get_chatgpt_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get the authenticated ChatGPT user from the request.

    Args:
        request: The Starlette request object

    Returns:
        User info dict if authenticated via ChatGPT, None otherwise
    """
    if hasattr(request.state, "chatgpt_user"):
        return request.state.chatgpt_user
    return None


def is_chatgpt_authenticated(request: Request) -> bool:
    """
    Check if the request is authenticated via ChatGPT.

    Args:
        request: The Starlette request object

    Returns:
        True if authenticated via ChatGPT, False otherwise
    """
    return getattr(request.state, "chatgpt_authenticated", False)

