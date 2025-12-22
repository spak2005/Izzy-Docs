"""
OpenAI Apps SDK Manifest Generation

Generates the app manifest (ai-plugin.json) and MCP manifest required
for ChatGPT integration via the OpenAI Apps SDK.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from importlib import metadata

logger = logging.getLogger(__name__)


def get_app_manifest(
    base_url: Optional[str] = None,
    external_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate the OpenAI Apps SDK app manifest (ai-plugin.json).

    This manifest describes the app to ChatGPT and provides information
    about authentication, API endpoints, and app metadata.

    Args:
        base_url: The base URL of the MCP server (e.g., http://localhost:8000)
        external_url: Optional external URL for production deployments

    Returns:
        Dictionary containing the app manifest
    """
    # Get version from package metadata
    try:
        version = metadata.version("google-docs-mcp")
    except metadata.PackageNotFoundError:
        version = "1.0.0"

    # Determine effective URL
    effective_url = external_url or base_url or os.getenv(
        "WORKSPACE_EXTERNAL_URL",
        os.getenv("WORKSPACE_MCP_BASE_URI", "http://localhost") + ":" +
        os.getenv("PORT", os.getenv("WORKSPACE_MCP_PORT", "8000"))
    )

    # Build manifest
    manifest = {
        "schema_version": "v1",
        "name_for_human": "Google Docs",
        "name_for_model": "google_workspace",
        "description_for_human": "Create, read, edit, and manage Google Docs documents with AI assistance.",
        "description_for_model": (
            "A powerful tool for interacting with Google Docs. Use this to create new documents, "
            "read document content, insert and format text, add tables and images, manage headers "
            "and footers, find and replace text, apply paragraph styles, and export documents to PDF. "
            "Also includes Google Drive integration for searching, listing, and managing files."
        ),
        "auth": {
            "type": "oauth",
            "client_url": f"{effective_url}/oauth2/authorize",
            "authorization_url": f"{effective_url}/oauth2/token",
            "authorization_content_type": "application/json",
            "scope": " ".join(_get_required_scopes()),
            "verification_tokens": {
                "openai": os.getenv("OPENAI_VERIFICATION_TOKEN", "")
            }
        },
        "api": {
            "type": "mcp",
            "url": f"{effective_url}/mcp",
            "is_user_authenticated": True,
        },
        "logo_url": f"{effective_url}/logo.png",
        "contact_email": os.getenv("APP_CONTACT_EMAIL", "support@example.com"),
        "legal_info_url": os.getenv("APP_LEGAL_INFO_URL", f"{effective_url}/legal"),
        "version": version,
    }

    return manifest


def get_mcp_manifest(
    base_url: Optional[str] = None,
    external_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate the MCP server manifest.

    This manifest describes the MCP server's capabilities and tools
    for ChatGPT and other MCP clients.

    Args:
        base_url: The base URL of the MCP server
        external_url: Optional external URL for production deployments

    Returns:
        Dictionary containing the MCP manifest
    """
    try:
        version = metadata.version("google-docs-mcp")
    except metadata.PackageNotFoundError:
        version = "1.0.0"

    effective_url = external_url or base_url or os.getenv(
        "WORKSPACE_EXTERNAL_URL",
        os.getenv("WORKSPACE_MCP_BASE_URI", "http://localhost") + ":" +
        os.getenv("PORT", os.getenv("WORKSPACE_MCP_PORT", "8000"))
    )

    manifest = {
        "name": "google_workspace",
        "version": version,
        "description": "Google Docs and Drive MCP Server for document creation and management",
        "transport": {
            "type": "streamable-http",
            "url": f"{effective_url}/mcp",
        },
        "authentication": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"{effective_url}/oauth2/authorize",
                    "tokenUrl": f"{effective_url}/oauth2/token",
                    "scopes": _get_scopes_description(),
                }
            }
        },
        "tools": _get_tools_summary(),
        "capabilities": {
            "documents": {
                "create": True,
                "read": True,
                "update": True,
                "delete": False,  # Docs API doesn't support delete directly
            },
            "drive": {
                "search": True,
                "upload": True,
                "download": True,
                "share": True,
            },
            "formatting": {
                "text": True,
                "paragraph": True,
                "tables": True,
                "images": True,
                "headers_footers": True,
            }
        }
    }

    return manifest


def get_oauth_metadata(
    base_url: Optional[str] = None,
    external_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate OAuth 2.1 Authorization Server Metadata per RFC 8414.

    This is used by ChatGPT and other OAuth clients for discovery.

    Args:
        base_url: The base URL of the MCP server
        external_url: Optional external URL for production deployments

    Returns:
        Dictionary containing the OAuth metadata
    """
    effective_url = external_url or base_url or os.getenv(
        "WORKSPACE_EXTERNAL_URL",
        os.getenv("WORKSPACE_MCP_BASE_URI", "http://localhost") + ":" +
        os.getenv("PORT", os.getenv("WORKSPACE_MCP_PORT", "8000"))
    )

    return {
        "issuer": effective_url,
        "authorization_endpoint": f"{effective_url}/oauth2/authorize",
        "token_endpoint": f"{effective_url}/oauth2/token",
        "registration_endpoint": f"{effective_url}/oauth2/register",
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
        "service_documentation": f"{effective_url}/docs",
    }


def _get_required_scopes() -> List[str]:
    """Get the list of required OAuth scopes."""
    from auth.scopes import get_current_scopes
    return get_current_scopes()


def _get_scopes_description() -> Dict[str, str]:
    """Get scope descriptions for OAuth metadata."""
    return {
        "openid": "OpenID Connect authentication",
        "https://www.googleapis.com/auth/userinfo.email": "Access to user email address",
        "https://www.googleapis.com/auth/userinfo.profile": "Access to user profile information",
        "https://www.googleapis.com/auth/documents": "Full access to Google Docs",
        "https://www.googleapis.com/auth/documents.readonly": "Read-only access to Google Docs",
        "https://www.googleapis.com/auth/drive": "Full access to Google Drive",
        "https://www.googleapis.com/auth/drive.readonly": "Read-only access to Google Drive",
        "https://www.googleapis.com/auth/drive.file": "Access to files created by this app",
    }


def _get_tools_summary() -> List[Dict[str, str]]:
    """Get a summary of available tools for the manifest."""
    return [
        {
            "name": "search_docs",
            "description": "Search for Google Docs by name",
            "category": "documents",
        },
        {
            "name": "get_doc_content",
            "description": "Retrieve content of a Google Doc",
            "category": "documents",
        },
        {
            "name": "create_doc",
            "description": "Create a new Google Doc",
            "category": "documents",
        },
        {
            "name": "modify_doc_text",
            "description": "Insert, replace, or format text in a document",
            "category": "documents",
        },
        {
            "name": "find_and_replace_doc",
            "description": "Find and replace text throughout a document",
            "category": "documents",
        },
        {
            "name": "create_table_with_data",
            "description": "Create and populate a table in a document",
            "category": "documents",
        },
        {
            "name": "insert_doc_image",
            "description": "Insert an image into a document",
            "category": "documents",
        },
        {
            "name": "export_doc_to_pdf",
            "description": "Export a document to PDF format",
            "category": "documents",
        },
        {
            "name": "apply_paragraph_style",
            "description": "Apply paragraph-level formatting",
            "category": "formatting",
        },
        {
            "name": "search_drive_files",
            "description": "Search for files in Google Drive",
            "category": "drive",
        },
        {
            "name": "list_drive_items",
            "description": "List files and folders in Drive",
            "category": "drive",
        },
        {
            "name": "create_drive_file",
            "description": "Create a new file in Google Drive",
            "category": "drive",
        },
        {
            "name": "share_drive_file",
            "description": "Share a file or folder with others",
            "category": "drive",
        },
    ]

