FROM python:3.11-slim

# Install system dependencies for spaCy and VADER
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Expose entry point
ENTRYPOINT ["python", "app/main.py"]
