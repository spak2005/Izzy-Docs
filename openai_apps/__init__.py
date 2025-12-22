"""
OpenAI Apps SDK Integration Module

This module provides components for making the Google Docs MCP server
compatible with the OpenAI Apps SDK for ChatGPT integration.

Key Features:
- App manifest (ai-plugin.json) for ChatGPT discovery
- OAuth 2.1 metadata endpoints for automatic configuration
- MCP manifest for tool discovery
- ChatGPT authentication middleware for bearer token handling

Usage:
    The OpenAI Apps SDK routes are automatically enabled when running
    the server in streamable-http mode. Set OPENAI_APPS_SDK_ENABLED=false
    to disable if not needed.

Endpoints:
    - /.well-known/ai-plugin.json - ChatGPT app manifest
    - /.well-known/oauth-authorization-server - OAuth 2.1 discovery
    - /mcp-manifest - MCP server capabilities manifest
    - /oauth2/authorize - OAuth authorization redirect
    - /oauth2/token - OAuth token exchange
    - /docs - API documentation
    - /legal - Legal information page
"""

from openai_apps.manifest import (
    get_app_manifest,
    get_mcp_manifest,
    get_oauth_metadata,
)
from openai_apps.routes import register_openai_apps_routes
from openai_apps.chatgpt_auth import (
    ChatGPTAuthMiddleware,
    get_chatgpt_user,
    is_chatgpt_authenticated,
)

__all__ = [
    # Manifest generation
    "get_app_manifest",
    "get_mcp_manifest",
    "get_oauth_metadata",
    # Route registration
    "register_openai_apps_routes",
    # ChatGPT authentication
    "ChatGPTAuthMiddleware",
    "get_chatgpt_user",
    "is_chatgpt_authenticated",
]

