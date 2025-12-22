# Testing the OpenAI Apps SDK Integration

This guide walks you through testing your Google Docs MCP server with OpenAI Apps SDK locally before deploying.

## Prerequisites

1. **Google Cloud Project** with OAuth 2.0 credentials
2. **Python 3.10+** installed
3. **ngrok** for exposing local server with HTTPS (required for OAuth)

---

## Step 1: Set Up Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable APIs:
   - Google Docs API
   - Google Drive API
4. Go to **APIs & Services → Credentials**
5. Create **OAuth 2.0 Client ID** (Web application type)
6. Add these **Authorized redirect URIs**:
   - `http://localhost:8000/oauth2callback`
   - `http://localhost:8000/oauth2/authorize`
   - Your ngrok URL (add after Step 3): `https://YOUR-NGROK-URL.ngrok-free.app/oauth2callback`

---

## Step 2: Create Your `.env` File

Create a `.env` file in the project root:

```bash
cd /Users/israelogbonna/Documents/Builds/google_workspace_mcp
touch .env
```

Add these environment variables:

```env
# Required: Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Server Configuration
PORT=8000
WORKSPACE_MCP_BASE_URI=http://localhost

# OAuth 2.1 Mode (required for OpenAI Apps SDK)
MCP_ENABLE_OAUTH21=true

# OpenAI Apps SDK
OPENAI_APPS_SDK_ENABLED=true
APP_CONTACT_EMAIL=your-email@example.com

# Development
OAUTHLIB_INSECURE_TRANSPORT=1
```

---

## Step 3: Start ngrok for HTTPS Tunnel

ChatGPT requires HTTPS. Use ngrok to expose your local server:

```bash
# Install ngrok if you don't have it
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start ngrok tunnel
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

**Important**: Add this URL to your Google OAuth redirect URIs:
- `https://abc123.ngrok-free.app/oauth2callback`

Update your `.env` file:

```env
WORKSPACE_EXTERNAL_URL=https://abc123.ngrok-free.app
```

---

## Step 4: Start the MCP Server

In a new terminal:

```bash
cd /Users/israelogbonna/Documents/Builds/google_workspace_mcp

# Install dependencies
uv sync

# Run with streamable-http transport
uv run python main.py --transport streamable-http
```

You should see output like:

```
🔧 Google Docs MCP Server
===================================
📋 Server Information:
   📦 Version: 1.1.0
   🌐 Transport: streamable-http
   🔗 URL: https://abc123.ngrok-free.app
   🔐 OAuth Callback: https://abc123.ngrok-free.app/oauth2callback
...
✅ Ready for MCP connections
```

---

## Step 5: Test the Endpoints

### Test Health Check:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "workspace-mcp", "version": "dev", "transport": "streamable-http"}
```

### Test App Manifest (OpenAI Apps SDK):

```bash
curl http://localhost:8000/.well-known/ai-plugin.json
```

Expected response:
```json
{
  "schema_version": "v1",
  "name_for_human": "Google Docs",
  "name_for_model": "google_docs",
  "description_for_human": "Create, read, edit, and manage Google Docs...",
  "auth": {
    "type": "oauth",
    "client_url": "https://abc123.ngrok-free.app/oauth2/authorize",
    ...
  },
  "api": {
    "type": "mcp",
    "url": "https://abc123.ngrok-free.app/mcp"
  },
  ...
}
```

### Test OAuth Metadata:

```bash
curl http://localhost:8000/.well-known/oauth-authorization-server
```

### Test MCP Manifest:

```bash
curl http://localhost:8000/mcp-manifest
```

### Test API Documentation:

Open in browser: `http://localhost:8000/docs`

---

## Step 6: Test OAuth Flow

1. Open your browser to:
   ```
   http://localhost:8000/oauth2/authorize?client_id=test&redirect_uri=http://localhost:8000/oauth2callback&response_type=code&state=test123
   ```

2. You should be redirected to Google's OAuth consent page
3. After authorization, you'll be redirected back with credentials stored

---

## Step 7: Test with MCP Inspector (Optional)

You can use FastMCP's built-in tools to test the MCP functionality:

```bash
# Install mcp-inspector if not already installed
uv pip install mcp

# Connect to your server
mcp dev http://localhost:8000/mcp
```

---

## Step 8: Test with ChatGPT Developer Mode

Once everything works locally:

1. **Enable Developer Mode** in ChatGPT:
   - Business/Enterprise users: Enable from Workspace settings
   - Personal: May need to apply for access

2. **Create a Custom App**:
   - Go to ChatGPT → Settings → Custom Apps
   - Add your ngrok URL: `https://abc123.ngrok-free.app/.well-known/ai-plugin.json`

3. **Test the Integration**:
   - Start a new chat
   - Ask ChatGPT to "Create a new Google Doc called Test Document"
   - Complete the OAuth flow when prompted
   - Verify the document was created

---

## Troubleshooting

### "OAuth callback URL doesn't match"
- Make sure your ngrok URL is added to Google Cloud Console authorized redirect URIs
- Make sure `WORKSPACE_EXTERNAL_URL` in `.env` matches your ngrok URL

### "Invalid client_id"
- Double-check your `GOOGLE_OAUTH_CLIENT_ID` in `.env`

### "Port already in use"
```bash
# Find what's using port 8000
lsof -i :8000
# Kill it if needed
kill -9 <PID>
```

### "ngrok URL changed"
ngrok free tier gives you a new URL each time. Update:
1. Google Cloud Console redirect URIs
2. `WORKSPACE_EXTERNAL_URL` in `.env`
3. Restart the server

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_OAUTH_CLIENT_ID` | ✅ | - | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | ✅ | - | Google OAuth client secret |
| `PORT` | ❌ | 8000 | Server port |
| `WORKSPACE_MCP_BASE_URI` | ❌ | http://localhost | Base URI |
| `WORKSPACE_EXTERNAL_URL` | ❌ | - | Public URL (ngrok/production) |
| `MCP_ENABLE_OAUTH21` | ❌ | false | Enable OAuth 2.1 mode |
| `OPENAI_APPS_SDK_ENABLED` | ❌ | true | Enable OpenAI Apps SDK routes |
| `APP_CONTACT_EMAIL` | ❌ | support@example.com | Contact email in manifest |
| `OAUTHLIB_INSECURE_TRANSPORT` | ❌ | 0 | Allow OAuth over HTTP (dev only) |

---

## Quick Start Commands

```bash
# 1. Set up environment
cd /Users/israelogbonna/Documents/Builds/google_workspace_mcp
cat > .env << 'EOF'
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
PORT=8000
MCP_ENABLE_OAUTH21=true
OPENAI_APPS_SDK_ENABLED=true
OAUTHLIB_INSECURE_TRANSPORT=1
EOF

# 2. Start ngrok (in terminal 1)
ngrok http 8000

# 3. Update .env with ngrok URL
echo "WORKSPACE_EXTERNAL_URL=https://YOUR-NGROK-URL.ngrok-free.app" >> .env

# 4. Start server (in terminal 2)
uv run python main.py --transport streamable-http

# 5. Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/.well-known/ai-plugin.json
```

