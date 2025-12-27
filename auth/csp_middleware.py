"""
Content Security Policy (CSP) Middleware

Adds CSP headers required for OpenAI Apps SDK submission.
These headers tell browsers and OpenAI what domains the app is allowed to fetch from.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Domains that IzzyDocs connects to
ALLOWED_CONNECT_DOMAINS = [
    "'self'",  # Same origin
    "https://accounts.google.com",  # OAuth authorization
    "https://oauth2.googleapis.com",  # Token exchange
    "https://www.googleapis.com",  # Google APIs
    "https://docs.googleapis.com",  # Google Docs API
    "https://drive.googleapis.com",  # Google Drive API
    "https://openidconnect.googleapis.com",  # User info
]


class CSPMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds Content Security Policy headers to all responses.
    
    Required for OpenAI Apps SDK submission to declare what domains
    the app fetches from.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Build CSP header
        connect_src = " ".join(ALLOWED_CONNECT_DOMAINS)
        
        csp_policy = (
            f"default-src 'self'; "
            f"connect-src {connect_src}; "
            f"script-src 'self' 'unsafe-inline'; "
            f"style-src 'self' 'unsafe-inline'; "
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com; "
            f"frame-ancestors 'self' https://chatgpt.com https://chat.openai.com"
        )
        
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Also add other security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

