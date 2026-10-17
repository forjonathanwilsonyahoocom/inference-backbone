# --- Stage 1: Build virtual environment ---
FROM python:3.12-slim AS compiler
ENV PYTHONUNBUFFERED=1
WORKDIR /app/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# install deps
COPY ./docker-broker/requirements.txt /app/requirements.txt
RUN pip install -Ur requirements.txt

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim AS runner
ENV PYTHONUNBUFFERED=1
WORKDIR /app/

COPY --from=compiler /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./docker-broker/app/ .
COPY ./contracts/ /tmp/contracts/
RUN pip install --no-cache-dir /tmp/contracts
COPY ./observability/ /tmp/observability/
RUN pip install --no-cache-dir /tmp/observability
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
