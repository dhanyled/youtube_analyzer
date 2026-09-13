# Multi-stage Dockerfile for YouTube Analyzer & MCP Server
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code and build project
COPY src/ ./src/
COPY README.md ./
RUN uv sync --frozen --no-dev

# Final production stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV DATABASE_URL="sqlite:////app/data/youtube_analyzer.db"
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["python", "-m", "youtube_analyzer.server.mcp_server"]
