# Use Astral's official uv image with Python 3.11
FROM ghcr.io/astral-sh/uv:python3.11

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies from uv.lock
RUN uv sync --frozen

# Copy the rest of your code
COPY . .

# Run your MCP (adjust main.py if your entry point is different)
CMD ["python", "server.py"]
