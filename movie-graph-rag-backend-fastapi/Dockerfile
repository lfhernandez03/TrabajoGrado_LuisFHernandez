FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies (wget + netcat for entrypoint + gcc for build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    wget \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY app/ ./app/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run entrypoint (waits for Fuseki/MongoDB before starting FastAPI)
CMD ["./entrypoint.sh"]
