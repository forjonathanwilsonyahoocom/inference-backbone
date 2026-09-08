# Dockerfile for doc-ingestor
# Use Python 3.12 slim base image
FROM python:3.12-slim

# Install git
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose health check port (optional)
RUN chmod +x entrypoint.sh
