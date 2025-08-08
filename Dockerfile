# Use a valid derived image with Python 3.11 + uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set working directory
WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (leveraging cache for speed)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Copy application code
COPY . .

# Final dependency sync (including project code)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Default command (adjust if your entrypoint differs)
CMD ["python", "main.py"]
