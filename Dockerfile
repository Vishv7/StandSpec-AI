FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code, datasets, and release assets
COPY . .

# Hugging Face Spaces uses port 7860 by default
ENV PORT=7860
EXPOSE 7860

# Run Uvicorn server dynamically on configured port
CMD ["sh", "-c", "uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-7860}"]
