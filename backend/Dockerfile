# Multi-stage build for Python backend
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for faster dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# Ensure uv is on PATH (installer may place it in ~/.local/bin or ~/.cargo/bin)
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./
# Copy application code before editable install (required for -e . when using src layout)
COPY src/ ./src/

# Install dependencies (production + web extras) including editable package
RUN uv pip install --system -e ".[web,visualization,streaming]"

# Create data directory
RUN mkdir -p /app/data

# Expose port for HTTP API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the HTTP API server
CMD ["uvicorn", "household_mcp.web.http_server:create_http_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
