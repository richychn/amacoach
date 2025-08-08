# Use official Python 3.12 slim image
FROM python:3.12-slim-bookworm

# Install curl and ca-certificates needed for uv installer
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and run uv installer script
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency manifests first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies locked by uv.lock
RUN uv sync --frozen

# Copy the rest of your app source code
COPY . .

# Expose the port Railway uses (default 8080)
EXPOSE 8080

# Set the command to run your MCP app; adjust "your_module" accordingly
CMD ["uv", "run", "python", "-m", "server.py"]
