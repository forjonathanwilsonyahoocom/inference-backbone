FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install dependencies
COPY validator-agent/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -Ur requirements.txt

# Copy the application code
COPY validator-agent/app/ /app

# Install local packages
COPY contracts/ /tmp/contracts/
RUN pip install --no-cache-dir /tmp/contracts
COPY observability/ /tmp/observability/
RUN pip install --no-cache-dir /tmp/observability
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

