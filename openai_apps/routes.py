"""
OpenAI Apps SDK Routes

Registers HTTP routes required for OpenAI Apps SDK / ChatGPT integration.
These include well-known endpoints, manifests, and OAuth discovery.
"""

import logging
import os
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from starlette.requests import Request

from openai_apps.manifest import (
    get_app_manifest,
    get_mcp_manifest,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def _get_required_scopes():
    """Get the list of required OAuth scopes."""
    from auth.scopes import get_current_scopes
    return get_current_scopes()


def register_openai_apps_routes(server: "FastMCP") -> None:
    """
    Register OpenAI Apps SDK routes on the FastMCP server.

    This adds endpoints required for ChatGPT integration:
    - /.well-known/ai-plugin.json - App manifest for ChatGPT
    - /.well-known/oauth-authorization-server - OAuth 2.1 discovery
    - /mcp-manifest - MCP server manifest
    - /openapi.json - OpenAPI schema (if needed)
    - /logo.png - App logo

    Args:
        server: The FastMCP server instance to register routes on
    """
    from auth.oauth_config import get_oauth_config

    config = get_oauth_config()
    base_url = config.base_url
    external_url = config.external_url

    @server.custom_route("/.well-known/ai-plugin.json", methods=["GET"])
    async def ai_plugin_manifest(request: Request) -> JSONResponse:
        """
        OpenAI Apps SDK app manifest endpoint.

        This is the primary discovery endpoint that ChatGPT uses to understand
        the app's capabilities, authentication requirements, and API location.
        """
        logger.info("Serving ai-plugin.json manifest")
        manifest = get_app_manifest(base_url=base_url, external_url=external_url)
        return JSONResponse(manifest)

    @server.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
    async def oauth_discovery(request: Request) -> JSONResponse:
        """
        OAuth 2.1 Authorization Server Metadata endpoint (RFC 8414).

        Used by OAuth clients for automatic configuration discovery.
        """
        logger.info("Serving OAuth authorization server metadata")
        effective_url = external_url or base_url
        metadata = {
            "issuer": effective_url,
            "authorization_endpoint": f"{effective_url}/authorize",
            "token_endpoint": f"{effective_url}/token",
            "registration_endpoint": f"{effective_url}/register",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
                "client_secret_basic",
            ],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": _get_required_scopes(),
            "claims_supported": ["sub", "email", "name", "picture"],
        }
        return JSONResponse(metadata)

    @server.custom_route("/.well-known/openid-configuration", methods=["GET"])
    async def openid_configuration(request: Request) -> JSONResponse:
        """
        OpenID Connect Discovery endpoint.

        Required by ChatGPT for proper OAuth/OIDC integration.
        """
        logger.info("Serving OpenID Connect configuration")
        effective_url = external_url or base_url
        return JSONResponse({
            "issuer": effective_url,
            "authorization_endpoint": f"{effective_url}/authorize",
            "token_endpoint": f"{effective_url}/token",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "registration_endpoint": f"{effective_url}/register",
            "response_types_supported": ["code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "scopes_supported": _get_required_scopes(),
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "claims_supported": ["sub", "email", "name", "picture", "email_verified"],
            "code_challenge_methods_supported": ["S256"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
        })

    @server.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
    async def oauth_protected_resource(request: Request) -> JSONResponse:
        """
        OAuth 2.0 Protected Resource Metadata (RFC 9728).
        
        Tells clients which authorization server protects this resource.
        """
        logger.info("Serving OAuth protected resource metadata")
        effective_url = external_url or base_url
        return JSONResponse({
            "resource": f"{effective_url}/mcp",
            "authorization_servers": [effective_url],
            "scopes_supported": _get_required_scopes(),
        })

    @server.custom_route("/.well-known/oauth-protected-resource/mcp", methods=["GET"])
    async def oauth_protected_resource_mcp(request: Request) -> JSONResponse:
        """OAuth protected resource metadata for /mcp path."""
        logger.info("Serving OAuth protected resource metadata for /mcp")
        effective_url = external_url or base_url
        return JSONResponse({
            "resource": f"{effective_url}/mcp",
            "authorization_servers": [effective_url],
            "scopes_supported": _get_required_scopes(),
        })

    @server.custom_route("/register", methods=["POST"])
    async def register_client(request: Request) -> JSONResponse:
        """
        OAuth 2.0 Dynamic Client Registration (RFC 7591).
        
        Allows ChatGPT to register itself as an OAuth client.
        """
        import secrets as secrets_module
        import time

        try:
            body = await request.json()
        except Exception:
            body = {}

        client_name = body.get("client_name", "ChatGPT Client")
        redirect_uris = body.get("redirect_uris", [])

        # Generate client credentials
        client_id = secrets_module.token_hex(16)
        client_secret = secrets_module.token_hex(32)

        logger.info(f"Registered new client: {client_name} with id {client_id[:8]}...")

        response = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "client_secret_post",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_id_issued_at": int(time.time()),
        }

        return JSONResponse(response, status_code=201)

    @server.custom_route("/mcp-manifest", methods=["GET"])
    async def mcp_manifest(request: Request) -> JSONResponse:
        """
        MCP server manifest endpoint.

        Describes the MCP server's capabilities, tools, and transport configuration.
        """
        logger.info("Serving MCP manifest")
        manifest = get_mcp_manifest(base_url=base_url, external_url=external_url)
        return JSONResponse(manifest)

    # Override FastMCP's /authorize to go directly to Google OAuth
    @server.custom_route("/authorize", methods=["GET"])
    async def authorize_override(request: Request) -> HTMLResponse:
        """
        Override FastMCP's /authorize endpoint.
        
        This bypasses FastMCP's consent page and redirects directly to Google OAuth.
        Accepts any client_id (including dynamically registered ones from ChatGPT).
        """
        from urllib.parse import urlencode
        from auth.scopes import get_current_scopes
        import secrets

        # Extract OAuth parameters from request
        client_id = request.query_params.get("client_id")
        redirect_uri = request.query_params.get("redirect_uri")
        response_type = request.query_params.get("response_type", "code")
        scope = request.query_params.get("scope", "")
        state = request.query_params.get("state", "")
        code_challenge = request.query_params.get("code_challenge")

        logger.info(f"Custom /authorize called: client_id={client_id[:20] if client_id else 'none'}..., redirect_uri={redirect_uri}")

        # Generate our own state if none provided (or append to existing)
        internal_state = secrets.token_urlsafe(16)
        combined_state = f"{state}|{internal_state}" if state else internal_state

        # Build Google OAuth URL
        google_auth_base = "https://accounts.google.com/o/oauth2/v2/auth"

        # Merge requested scopes with required scopes
        requested_scopes = set(scope.split()) if scope else set()
        required_scopes = set(get_current_scopes())
        all_scopes = requested_scopes.union(required_scopes)

        # Use our callback URL
        our_callback = f"{external_url or base_url}/google-oauth-callback"

        params = {
            "client_id": config.client_id,
            "redirect_uri": our_callback,
            "response_type": response_type,
            "scope": " ".join(all_scopes),
            "state": combined_state,
            "access_type": "offline",
            "prompt": "consent",
        }

        # NOTE: Do NOT pass ChatGPT's PKCE code_challenge to Google.
        # ChatGPT uses PKCE between ChatGPT <-> our server.
        # We use a separate OAuth flow between our server <-> Google (without PKCE).

        google_auth_url = f"{google_auth_base}?{urlencode(params)}"

        # Store the state with client info for callback handling
        from auth.oauth21_session_store import get_oauth21_session_store
        store = get_oauth21_session_store()
        store.store_oauth_state(
            state=combined_state,
            session_id=None,
            expires_in_seconds=600,
            metadata={
                "client_redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_state": state,
                "code_challenge": code_challenge,
                "internal_state": internal_state,
            }
        )

        logger.info("Redirecting to Google OAuth...")

        # Return redirect response
        return HTMLResponse(
            content=f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta http-equiv="refresh" content="0;url={google_auth_url}">
                <title>Redirecting to Google...</title>
            </head>
            <body>
                <p>Redirecting to Google for authentication...</p>
                <p>If you are not redirected, <a href="{google_auth_url}">click here</a>.</p>
            </body>
            </html>
            ''',
            status_code=302,
            headers={"Location": google_auth_url}
        )

    @server.custom_route("/oauth2/authorize", methods=["GET"])
    async def oauth2_authorize(request: Request) -> HTMLResponse:
        """
        OAuth 2.0/2.1 authorization endpoint.

        Redirects to Google's OAuth consent page for user authorization.
        This endpoint is called by ChatGPT when initiating OAuth flow.
        """
        from urllib.parse import urlencode
        from auth.scopes import get_current_scopes
        import secrets

        # Extract OAuth parameters from request
        client_id = request.query_params.get("client_id")
        redirect_uri = request.query_params.get("redirect_uri")
        response_type = request.query_params.get("response_type", "code")
        scope = request.query_params.get("scope", "")
        state = request.query_params.get("state", "")
        code_challenge = request.query_params.get("code_challenge")

        logger.info(f"OAuth authorize request: client_id={client_id}, redirect_uri={redirect_uri}, state={state[:20] if state else 'none'}...")

        # Generate our own state if none provided (or append to existing)
        internal_state = secrets.token_urlsafe(16)
        combined_state = f"{state}|{internal_state}" if state else internal_state

        # Build Google OAuth URL
        google_auth_base = "https://accounts.google.com/o/oauth2/v2/auth"

        # Merge requested scopes with required scopes
        requested_scopes = set(scope.split()) if scope else set()
        required_scopes = set(get_current_scopes())
        all_scopes = requested_scopes.union(required_scopes)

        # Use our callback URL (not the client's redirect_uri - we'll redirect to that after)
        # Use /google-oauth-callback to avoid conflict with FastMCP's /oauth2callback
        our_callback = f"{external_url or base_url}/google-oauth-callback"

        params = {
            "client_id": config.client_id,
            "redirect_uri": our_callback,
            "response_type": response_type,
            "scope": " ".join(all_scopes),
            "state": combined_state,
            "access_type": "offline",
            "prompt": "consent",
        }

        # NOTE: Do NOT pass ChatGPT's PKCE code_challenge to Google.
        # ChatGPT uses PKCE between ChatGPT <-> our server.
        # We use a separate OAuth flow between our server <-> Google (without PKCE).

        google_auth_url = f"{google_auth_base}?{urlencode(params)}"

        # Store the state with client info for callback handling
        from auth.oauth21_session_store import get_oauth21_session_store
        store = get_oauth21_session_store()
        store.store_oauth_state(
            state=combined_state,
            session_id=None,
            expires_in_seconds=600,
            metadata={
                "client_redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_state": state,
                "code_challenge": code_challenge,
                "internal_state": internal_state,
            }
        )

        logger.info("Stored OAuth state, redirecting to Google OAuth...")

        # Return redirect response
        return HTMLResponse(
            content=f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta http-equiv="refresh" content="0;url={google_auth_url}">
                <title>Redirecting to Google...</title>
            </head>
            <body>
                <p>Redirecting to Google for authentication...</p>
                <p>If you are not redirected, <a href="{google_auth_url}">click here</a>.</p>
            </body>
            </html>
            ''',
            status_code=302,
            headers={"Location": google_auth_url}
        )

    # Helper function for token exchange
    async def _handle_token_request(request: Request) -> JSONResponse:
        """
        Handle OAuth token requests.
        
        Checks if the code is one of our custom auth codes (from the callback)
        and returns stored tokens. For refresh tokens, exchanges with Google.
        """
        import httpx
        from auth.oauth21_session_store import get_oauth21_session_store

        try:
            # Parse request body
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.json()
            else:
                form_data = await request.form()
                body = dict(form_data)

            grant_type = body.get("grant_type")
            code = body.get("code")
            redirect_uri = body.get("redirect_uri")
            _client_id = body.get("client_id")  # noqa: F841 - extracted for potential future use
            _client_secret = body.get("client_secret")  # noqa: F841 - extracted for potential future use
            code_verifier = body.get("code_verifier")  # PKCE
            refresh_token_param = body.get("refresh_token")

            logger.info(f"Token request: grant_type={grant_type}, code={'yes' if code else 'no'}")

            store = get_oauth21_session_store()

            if grant_type == "authorization_code" and code:
                # Check if this is one of our custom auth codes
                try:
                    auth_code_key = f"authcode:{code}"
                    state_info = store.validate_and_consume_oauth_state(auth_code_key, session_id=None)
                    
                    # Found our stored tokens! (metadata is merged at top level)
                    token_response = {
                        "access_token": state_info.get("access_token"),
                        "refresh_token": state_info.get("refresh_token"),
                        "expires_in": state_info.get("expires_in", 3600),
                        "token_type": state_info.get("token_type", "Bearer"),
                        "scope": state_info.get("scope", ""),
                    }
                    # Include id_token if present (required for OpenID Connect)
                    if state_info.get("id_token"):
                        token_response["id_token"] = state_info.get("id_token")
                    logger.info("Returned stored tokens for custom auth code")
                    return JSONResponse(token_response)
                except ValueError:
                    # Not one of our codes, try Google exchange
                    logger.info("Auth code not found in store, trying Google exchange")
                    pass

                # Try to exchange with Google (in case it's a direct Google code)
                token_data = {
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri or config.redirect_uri,
                }
                if code_verifier:
                    token_data["code_verifier"] = code_verifier

            elif grant_type == "refresh_token" and refresh_token_param:
                # Refresh token - exchange with Google
                token_data = {
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token_param,
                }
            else:
                return JSONResponse(
                    {"error": "unsupported_grant_type"},
                    status_code=400
                )

            # Exchange with Google
            google_token_url = "https://oauth2.googleapis.com/token"
            async with httpx.AsyncClient() as client:
                response = await client.post(google_token_url, data=token_data)

            if response.status_code != 200:
                logger.error(f"Google token exchange failed: {response.text}")
                return JSONResponse(
                    {"error": "invalid_grant", "error_description": "Token exchange failed"},
                    status_code=400
                )

            token_response = response.json()
            logger.info("Token exchange successful")

            # Store session if we have the tokens
            if token_response.get("access_token"):
                from auth.oauth21_session_store import get_oauth21_session_store
                store = get_oauth21_session_store()

                # Try to get user info to store session
                try:
                    from auth.google_auth import get_user_info
                    from google.oauth2.credentials import Credentials

                    creds = Credentials(
                        token=token_response["access_token"],
                        refresh_token=token_response.get("refresh_token"),
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=config.client_id,
                        client_secret=config.client_secret,
                    )
                    user_info = get_user_info(creds)
                    if user_info and user_info.get("email"):
                        store.store_session(
                            user_email=user_info["email"],
                            access_token=token_response["access_token"],
                            refresh_token=token_response.get("refresh_token"),
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=config.client_id,
                            client_secret=config.client_secret,
                            scopes=token_response.get("scope", "").split(),
                            issuer="https://accounts.google.com",
                        )
                        logger.info(f"Stored OAuth session for {user_info['email']}")
                except Exception as e:
                    logger.warning(f"Could not store session: {e}")

            return JSONResponse(token_response)

        except Exception as e:
            logger.error(f"Token endpoint error: {e}", exc_info=True)
            return JSONResponse(
                {"error": "server_error", "error_description": str(e)},
                status_code=500
            )

    # Override FastMCP's /token endpoint
    @server.custom_route("/token", methods=["POST"])
    async def token_override(request: Request) -> JSONResponse:
        """Override FastMCP's /token endpoint to use our token handler."""
        return await _handle_token_request(request)

    @server.custom_route("/oauth2/token", methods=["POST"])
    async def oauth2_token(request: Request) -> JSONResponse:
        """OAuth 2.0/2.1 token endpoint (alternate path)."""
        return await _handle_token_request(request)

    @server.custom_route("/google-oauth-callback", methods=["GET"])
    async def google_oauth_callback(request: Request) -> HTMLResponse:
        """
        Google OAuth callback endpoint.

        Handles the callback from Google after user authorization.
        Exchanges the code for tokens and redirects back to the client.
        Uses a different path to avoid conflict with FastMCP's /oauth2callback.
        """
        import httpx

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        logger.info(f"OAuth callback received: state={state[:20] if state else 'none'}..., code={'yes' if code else 'no'}, error={error}")

        if error:
            logger.error(f"OAuth callback error from Google: {error}")
            return HTMLResponse(
                content=f'''
                <!DOCTYPE html>
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Error: {error}</p>
                    <p>Please close this window and try again.</p>
                </body>
                </html>
                ''',
                status_code=400
            )

        if not code:
            logger.error("OAuth callback: No authorization code received")
            return HTMLResponse(
                content='''
                <!DOCTYPE html>
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>No authorization code received from Google.</p>
                    <p>Please close this window and try again.</p>
                </body>
                </html>
                ''',
                status_code=400
            )

        # Validate and retrieve state info
        from auth.oauth21_session_store import get_oauth21_session_store
        store = get_oauth21_session_store()

        try:
            state_info = store.validate_and_consume_oauth_state(state, session_id=None)
            logger.info("OAuth state validated successfully")
        except ValueError as e:
            logger.error(f"OAuth state validation failed: {e}")
            return HTMLResponse(
                content='''
                <!DOCTYPE html>
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Invalid or expired authorization session.</p>
                    <p>Please close this window and try again.</p>
                </body>
                </html>
                ''',
                status_code=400
            )

        # Exchange code for tokens with Google
        our_callback = f"{external_url or base_url}/google-oauth-callback"
        token_data = {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": our_callback,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=token_data
                )

            if response.status_code != 200:
                logger.error(f"Google token exchange failed: {response.text}")
                return HTMLResponse(
                    content='''
                    <!DOCTYPE html>
                    <html>
                    <head><title>Authentication Failed</title></head>
                    <body>
                        <h1>Authentication Failed</h1>
                        <p>Failed to exchange authorization code for tokens.</p>
                        <p>Please close this window and try again.</p>
                    </body>
                    </html>
                    ''',
                    status_code=400
                )

            token_response = response.json()
            logger.info("Token exchange with Google successful")

            # Get user info
            from auth.google_auth import get_user_info
            from google.oauth2.credentials import Credentials
            import secrets as secrets_module
            from urllib.parse import urlencode

            creds = Credentials(
                token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=config.client_id,
                client_secret=config.client_secret,
            )
            user_info = get_user_info(creds)
            user_email = user_info.get("email") if user_info else "Unknown"

            # Generate our own authorization code to give to ChatGPT
            auth_code = secrets_module.token_urlsafe(32)

            # Store the tokens with the auth code for later retrieval
            store.store_session(
                user_email=user_email,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=config.client_id,
                client_secret=config.client_secret,
                scopes=token_response.get("scope", "").split(),
                issuer="https://accounts.google.com",
            )

            # Also store the auth code -> tokens mapping for the token endpoint
            auth_code_metadata = {
                "access_token": token_response["access_token"],
                "refresh_token": token_response.get("refresh_token"),
                "expires_in": token_response.get("expires_in", 3600),
                "token_type": "Bearer",
                "scope": token_response.get("scope", ""),
            }
            # Include id_token if Google returned one (for OpenID Connect)
            if token_response.get("id_token"):
                auth_code_metadata["id_token"] = token_response["id_token"]
            
            store.store_oauth_state(
                state=f"authcode:{auth_code}",
                session_id=user_email,
                expires_in_seconds=300,
                metadata=auth_code_metadata
            )
            logger.info(f"Stored OAuth session and auth code for {user_email}")

            # Get the client's redirect URI from state (metadata is merged at top level)
            client_redirect_uri = state_info.get("client_redirect_uri")
            client_state = state_info.get("client_state", "")

            if client_redirect_uri:
                # Redirect back to ChatGPT with our auth code
                redirect_params = {"code": auth_code}
                if client_state:
                    redirect_params["state"] = client_state

                redirect_url = f"{client_redirect_uri}?{urlencode(redirect_params)}"
                logger.info(f"Redirecting to client: {redirect_url[:50]}...")

                return HTMLResponse(
                    content=f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta http-equiv="refresh" content="0;url={redirect_url}">
                        <title>Redirecting...</title>
                    </head>
                    <body>
                        <p>Authentication successful! Redirecting back to ChatGPT...</p>
                    </body>
                    </html>
                    ''',
                    status_code=302,
                    headers={"Location": redirect_url}
                )
            else:
                # No redirect URI, show success page
                return HTMLResponse(
                    content=f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Authentication Successful</title>
                        <style>
                            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                                   display: flex; justify-content: center; align-items: center; height: 100vh; 
                                   margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                            .card {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); 
                                    text-align: center; max-width: 400px; }}
                            h1 {{ color: #1a73e8; margin-bottom: 16px; }}
                            p {{ color: #5f6368; margin: 8px 0; }}
                            .email {{ font-weight: bold; color: #202124; }}
                            .checkmark {{ font-size: 48px; margin-bottom: 16px; }}
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <div class="checkmark">✅</div>
                            <h1>Authentication Successful!</h1>
                            <p>You are now signed in as:</p>
                            <p class="email">{user_email}</p>
                            <p style="margin-top: 24px; color: #9aa0a6;">You can close this window.</p>
                        </div>
                    </body>
                    </html>
                    '''
                )

        except Exception as e:
            logger.error(f"OAuth callback error: {e}", exc_info=True)
            return HTMLResponse(
                content='''
                <!DOCTYPE html>
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>An error occurred during authentication.</p>
                    <p>Please close this window and try again.</p>
                </body>
                </html>
                ''',
                status_code=500
            )

    @server.custom_route("/logo.png", methods=["GET"])
    async def logo(request: Request) -> FileResponse:
        """
        Serve the app logo.

        Returns a default logo or custom logo if configured.
        """
        from pathlib import Path

        # Check for custom logo
        custom_logo = os.getenv("APP_LOGO_PATH")
        if custom_logo and Path(custom_logo).exists():
            return FileResponse(custom_logo, media_type="image/png")

        # Check for logo in static directory
        static_logo = Path(__file__).parent.parent / "static" / "logo.png"
        if static_logo.exists():
            return FileResponse(str(static_logo), media_type="image/png")

        # Return a placeholder response
        return JSONResponse(
            {"error": "Logo not found"},
            status_code=404
        )

    @server.custom_route("/legal", methods=["GET"])
    async def legal_info(request: Request) -> HTMLResponse:
        """
        Legal information page.

        Provides terms of service and privacy information.
        """
        legal_url = os.getenv("APP_LEGAL_INFO_URL")
        if legal_url and legal_url != f"{external_url or base_url}/legal":
            return HTMLResponse(
                content=f'<meta http-equiv="refresh" content="0;url={legal_url}">',
                headers={"Location": legal_url},
                status_code=302
            )

        return HTMLResponse(
            content='''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Legal Information - Google Docs MCP</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    h1 { color: #1a73e8; }
                </style>
            </head>
            <body>
                <h1>Google Docs MCP - Legal Information</h1>
                <h2>Terms of Service</h2>
                <p>This application allows you to interact with Google Docs and Google Drive through ChatGPT.</p>
                <p>By using this application, you agree to:</p>
                <ul>
                    <li>Google's Terms of Service for Google Docs and Drive</li>
                    <li>OpenAI's Terms of Service for ChatGPT</li>
                    <li>Use the application responsibly and in compliance with all applicable laws</li>
                </ul>
                <h2>Privacy Policy</h2>
                <p>This application:</p>
                <ul>
                    <li>Only accesses Google services with your explicit OAuth authorization</li>
                    <li>Does not store your Google credentials permanently (uses OAuth tokens)</li>
                    <li>Does not share your data with third parties</li>
                    <li>Processes your documents only as requested through ChatGPT</li>
                </ul>
                <h2>Contact</h2>
                <p>For questions or concerns, please contact the application administrator.</p>
            </body>
            </html>
            '''
        )

    @server.custom_route("/docs", methods=["GET"])
    async def api_documentation(request: Request) -> HTMLResponse:
        """
        API documentation page.

        Provides documentation for developers integrating with the MCP server.
        """
        manifest = get_mcp_manifest(base_url=base_url, external_url=external_url)
        tools_html = ""
        for tool in manifest.get("tools", []):
            tools_html += f'''
            <div class="tool">
                <h3>{tool['name']}</h3>
                <p>{tool['description']}</p>
                <span class="category">{tool['category']}</span>
            </div>
            '''

        return HTMLResponse(
            content=f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Google Docs MCP - API Documentation</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
                    h1 {{ color: #1a73e8; }}
                    .tool {{ background: white; border-radius: 8px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                    .tool h3 {{ margin: 0 0 8px 0; color: #202124; }}
                    .tool p {{ margin: 0 0 8px 0; color: #5f6368; }}
                    .category {{ display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
                    .section {{ margin: 24px 0; }}
                    code {{ background: #f1f3f4; padding: 2px 6px; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <h1>Google Docs MCP - API Documentation</h1>
                <p>Version: {manifest.get('version', '1.0.0')}</p>
                
                <div class="section">
                    <h2>Transport</h2>
                    <p>Type: <code>{manifest.get('transport', {}).get('type', 'streamable-http')}</code></p>
                    <p>URL: <code>{manifest.get('transport', {}).get('url', '')}</code></p>
                </div>
                
                <div class="section">
                    <h2>Available Tools</h2>
                    {tools_html}
                </div>
                
                <div class="section">
                    <h2>Authentication</h2>
                    <p>This API uses OAuth 2.1 with PKCE for authentication.</p>
                    <p>Authorization URL: <code>{manifest.get('authentication', {}).get('flows', {}).get('authorizationCode', {}).get('authorizationUrl', '')}</code></p>
                    <p>Token URL: <code>{manifest.get('authentication', {}).get('flows', {}).get('authorizationCode', {}).get('tokenUrl', '')}</code></p>
                </div>
            </body>
            </html>
            '''
        )

    logger.info("Registered OpenAI Apps SDK routes")
