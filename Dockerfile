# Use a small Python base image
FROM python:3.11-slim

# Install curl (needed for uv installer) and any basic build deps
RUN apt-get update && apt-get install -y curl gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Astral package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy dependency files first (to leverage Docker layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy the rest of your application code
COPY . .

# Default command to run your MCP
CMD ["python", "main.py"]
