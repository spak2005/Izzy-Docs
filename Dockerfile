FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV OAUTHLIB_INSECURE_TRANSPORT=0

# Run with FastMCP CLI
CMD ["fastmcp", "run", "fastmcp_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]

