# Dockerfile for FastAPI service
FROM python:3.12-slim

WORKDIR /app

COPY ./backbone-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire fastapi package
COPY ./backbone-api .
COPY ./contracts/ /tmp/contracts/
RUN pip install --no-cache-dir /tmp/contracts
COPY ./observability/ /tmp/observability/
RUN pip install --no-cache-dir /tmp/observability

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
