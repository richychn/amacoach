# Use official Python base image
FROM python:3.10-slim

# Install uv (fast Python package manager)
RUN pip install --upgrade pip && pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./


# Compile requirements with uv, then install
RUN uv pip compile --generate-hashes pyproject.toml -o requirements.txt \
    && uv pip install --system --no-deps --require-hashes -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port (Railway uses $PORT env variable)
EXPOSE 8000

# Set environment variables for Railway
ENV PORT=8000

# Start the server
CMD ["python", "server.py"]
