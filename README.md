# Google Docs MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A Model Context Protocol (MCP) server for Google Docs API integration. Enables natural language control over Google Docs through AI assistants and developer tools.

## Features

- **Full Document Management**: Create, read, modify, and search Google Docs
- **Rich Text Editing**: Format text with bold, italic, underline, strikethrough, custom fonts, colors, and hyperlinks
- **Paragraph Styling**: Apply alignment (left, center, right, justified), line spacing, indentation, and named styles (headings, titles, subtitles)
- **Pattern-Based Formatting**: Find text by pattern and apply formatting without modifying content
- **Table Support**: Create and manage tables with data population
- **Document Structure**: Insert page breaks, lists, images, headers, and footers
- **Comment Management**: Read, create, reply to, and resolve document comments
- **PDF Export**: Export documents to PDF format
- **Drive Integration**: Search, share, and manage document files in Drive
- **OAuth 2.0/2.1 Support**: Secure authentication with automatic token management

## Prerequisites

- **Python 3.10+**
- **[uv](https://github.com/astral-sh/uv)** (for running the server)
- **Google Cloud Project** with OAuth 2.0 credentials

## Quick Start

### Choose Your Mode

Pick one runtime mode before setup:

- **STDIO (`main.py --transport stdio`)**: Best for local MCP clients like Claude Desktop.
- **Streamable HTTP (`main.py --transport streamable-http`)**: Best for remote clients, browser-based flows, and OpenAI Apps SDK endpoints.
- **FastMCP Cloud entrypoint (`fastmcp_server.py`)**: Cloud-oriented mode that enforces OAuth 2.1 and stateless defaults.

### 1. Google Cloud Setup

1. Create a new project in [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services → Credentials**
3. Click **Create Credentials → OAuth Client ID**
4. Choose **Desktop Application** as the application type
5. Download credentials and note the Client ID and Client Secret

### 2. Enable Required APIs

Enable these APIs in your Google Cloud Console:
- [Google Docs API](https://console.cloud.google.com/flows/enableapi?apiid=docs.googleapis.com)
- [Google Drive API](https://console.cloud.google.com/flows/enableapi?apiid=drive.googleapis.com) (required for search and comments)

### 3. Configure Environment

   ```bash
   export GOOGLE_OAUTH_CLIENT_ID="your-client-id"
   export GOOGLE_OAUTH_CLIENT_SECRET="your-secret"
export OAUTHLIB_INSECURE_TRANSPORT=1  # Development only
```

Or create a `.env` file in the project root:

```env
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-secret
OAUTHLIB_INSECURE_TRANSPORT=1
```

### 4. Start the Server

```bash
# Install dependencies
uv sync

# Run in stdio mode (default)
uv run main.py

# Run with HTTP transport
uv run main.py --transport streamable-http

# Single-user mode (simplified authentication)
uv run main.py --single-user
```

### Startup Commands by Mode

- **STDIO**: `uv run main.py`
- **Streamable HTTP**: `uv run main.py --transport streamable-http`
- **Single-user STDIO**: `uv run main.py --single-user`
- **FastMCP Cloud entrypoint**: `uv run fastmcp run fastmcp_server.py`

## Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "google_docs": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/google-docs-mcp",
        "main.py"
      ],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-secret",
        "OAUTHLIB_INSECURE_TRANSPORT": "1"
      }
    }
  }
}
```

## Available Tools

### Document Management
| Tool | Description |
|------|-------------|
| `search_docs` | Search for Google Docs by name |
| `get_doc_content` | Retrieve document content and text |
| `create_doc` | Create a new Google Doc |
| `list_docs_in_folder` | List documents in a Drive folder |
| `export_doc_to_pdf` | Export document to PDF format |
| `list_doc_tabs` | List all tabs in a document |

### Text Editing & Formatting
| Tool | Description |
|------|-------------|
| `modify_doc_text` | Insert, replace, or format text (bold, italic, underline, strikethrough, links, colors) |
| `find_and_replace_doc` | Find and replace text throughout a document |
| `format_matching_text` | Find text by pattern and apply formatting without modifying content |
| `apply_paragraph_style` | Apply paragraph-level styling (alignment, line spacing, named styles, indentation) |
| `append_to_doc` | Append text to the end of a document |
| `delete_doc_range` | Delete content within a specific range |
| `replace_doc_body` | Replace the entire document body while preserving the same doc ID |

### Document Structure
| Tool | Description |
|------|-------------|
| `insert_doc_elements` | Insert tables, lists, and page breaks |
| `insert_doc_image` | Insert images from Drive or URLs |
| `update_doc_headers_footers` | Modify document headers and footers |
| `batch_update_doc` | Execute multiple operations atomically |
| `inspect_doc_structure` | Analyze document structure and find insertion points |
| `get_doc_section_range` | Get character index boundaries for a named section |

### Tables
| Tool | Description |
|------|-------------|
| `create_table_with_data` | Create tables with data in one operation |
| `debug_table_structure` | Debug and inspect table structure |

### Comments
| Tool | Description |
|------|-------------|
| `read_document_comments` | Read all document comments |
| `create_document_comment` | Add a new comment to a document |
| `reply_to_document_comment` | Reply to an existing comment |
| `resolve_document_comment` | Resolve a comment |

### Drive Tools (for document management)
| Tool | Description |
|------|-------------|
| `search_drive_files` | Search for files in Google Drive |
| `get_drive_file_content` | Get file content from Drive |
| `get_drive_file_download_url` | Generate a temporary HTTP download URL for a Drive file |
| `list_drive_items` | List files and folders in a Drive folder |
| `create_drive_file` | Create a new Drive file from text, local path, or URL content |
| `update_drive_file` | Update file metadata (rename, move, star, trash) |
| `get_drive_shareable_link` | Generate or fetch a shareable Drive link |
| `share_drive_file` | Share a file with users, groups, or publicly |
| `batch_share_drive_file` | Apply multiple share operations in one request |
| `get_drive_file_permissions` | Check sharing permissions on a file |
| `check_drive_file_public_access` | Verify whether a file is publicly accessible |
| `update_drive_permission` | Modify an existing file permission |
| `remove_drive_permission` | Remove a specific file permission |
| `transfer_drive_ownership` | Transfer file ownership to another Google account |

### Authentication
| Tool | Description |
|------|-------------|
| `start_google_auth` | Manually initiate authentication |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID from Google Cloud | Required |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret | Required |
| `USER_GOOGLE_EMAIL` | Default email for single-user auth | None |
| `OAUTHLIB_INSECURE_TRANSPORT` | Allow HTTP for development | `0` |
| `WORKSPACE_MCP_PORT` | Server port for HTTP mode | `8000` |
| `WORKSPACE_MCP_BASE_URI` | Base server URI | `http://localhost` |
| `MCP_ENABLE_OAUTH21` | Enable OAuth 2.1 support | `false` |
| `WORKSPACE_MCP_STATELESS_MODE` | Stateless mode for containers | `false` |

## Project Structure

```
google-docs-mcp/
├── auth/              # Authentication system
│   ├── google_auth.py      # OAuth handling
│   ├── scopes.py           # Scope definitions
│   └── service_decorator.py # Service injection decorators
├── core/              # MCP server core
│   ├── server.py           # FastMCP server setup
│   ├── utils.py            # Utility functions
│   └── comments.py         # Comment management
├── gdocs/             # Google Docs tools
│   ├── docs_tools.py       # Main tool implementations
│   ├── docs_helpers.py     # Request builders
│   ├── docs_structure.py   # Document parsing
│   ├── docs_tables.py      # Table utilities
│   └── managers/           # Operation managers
├── main.py            # Server entry point
└── pyproject.toml     # Dependencies
```

## Development

### Adding New Tools

```python
from auth.service_decorator import require_google_service
from core.server import server

@server.tool()
@require_google_service("docs", "docs_read")
async def your_new_tool(service, user_google_email: str, document_id: str):
    """Your tool description"""
    # service is automatically injected
    result = service.documents().get(documentId=document_id).execute()
    return result
```

## Authentication Flow

1. When you first call a tool, the server returns an authorization URL
2. Open the URL in your browser and authorize access
3. Google provides an authorization code
4. The server completes authentication and retries your request
5. Credentials are cached for future requests

## Security

- Never commit `.env`, `client_secret.json`, or `.credentials/` to source control
- Use `OAUTHLIB_INSECURE_TRANSPORT=1` only in development
- Use HTTPS and OAuth 2.1 in production

## License

MIT License - see `LICENSE` file for details.
