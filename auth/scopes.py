"""
Google Docs OAuth Scopes

This module centralizes OAuth scope definitions for Google Docs MCP integration.
"""

import logging

logger = logging.getLogger(__name__)

# Global variable to store enabled tools (set by main.py)
_ENABLED_TOOLS = None

# Individual OAuth Scope Constants
USERINFO_EMAIL_SCOPE = "https://www.googleapis.com/auth/userinfo.email"
USERINFO_PROFILE_SCOPE = "https://www.googleapis.com/auth/userinfo.profile"
OPENID_SCOPE = "openid"

# Google Drive scopes (needed for docs search and comments)
# NOTE: Full DRIVE_SCOPE removed to avoid CASA security assessment requirement
# DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"  # Restricted - requires CASA
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"

# Google Docs scopes
DOCS_READONLY_SCOPE = "https://www.googleapis.com/auth/documents.readonly"
DOCS_WRITE_SCOPE = "https://www.googleapis.com/auth/documents"

# Base OAuth scopes required for user identification
BASE_SCOPES = [USERINFO_EMAIL_SCOPE, USERINFO_PROFILE_SCOPE, OPENID_SCOPE]

# Service-specific scope groups
DOCS_SCOPES = [DOCS_READONLY_SCOPE, DOCS_WRITE_SCOPE]
# NOTE: DRIVE_SCOPE removed - using readonly + file scopes to avoid CASA requirement
DRIVE_SCOPES = [DRIVE_READONLY_SCOPE, DRIVE_FILE_SCOPE]

# Tool-to-scopes mapping
TOOL_SCOPES_MAP = {
    "docs": DOCS_SCOPES + DRIVE_SCOPES,
    "drive": DRIVE_SCOPES,
}


def set_enabled_tools(enabled_tools):
    """
    Set the globally enabled tools list.

    Args:
        enabled_tools: List of enabled tool names.
    """
    global _ENABLED_TOOLS
    _ENABLED_TOOLS = enabled_tools
    logger.info(f"Enabled tools set for scope management: {enabled_tools}")


def get_current_scopes():
    """
    Returns scopes for currently enabled tools.
    Uses globally set enabled tools or all tools if not set.

    Returns:
        List of unique scopes for the enabled tools plus base scopes.
    """
    enabled_tools = _ENABLED_TOOLS
    if enabled_tools is None:
        # Default behavior - return docs scopes
        enabled_tools = ["docs"]

    # Start with base scopes (always required)
    scopes = BASE_SCOPES.copy()

    # Add scopes for each enabled tool
    for tool in enabled_tools:
        if tool in TOOL_SCOPES_MAP:
            scopes.extend(TOOL_SCOPES_MAP[tool])

    logger.debug(
        f"Generated scopes for tools {list(enabled_tools)}: {len(set(scopes))} unique scopes"
    )
    # Return unique scopes
    return list(set(scopes))


def get_scopes_for_tools(enabled_tools=None):
    """
    Returns scopes for enabled tools only.

    Args:
        enabled_tools: List of enabled tool names. If None, returns docs scopes.

    Returns:
        List of unique scopes for the enabled tools plus base scopes.
    """
    if enabled_tools is None:
        # Default behavior - return docs scopes
        enabled_tools = ["docs"]

    # Start with base scopes (always required)
    scopes = BASE_SCOPES.copy()

    # Add scopes for each enabled tool
    for tool in enabled_tools:
        if tool in TOOL_SCOPES_MAP:
            scopes.extend(TOOL_SCOPES_MAP[tool])

    # Return unique scopes
    return list(set(scopes))


# Combined scopes for Google Docs operations (backwards compatibility)
SCOPES = get_scopes_for_tools()
