# --- Stage 1: Build virtual environment ---
FROM python:3.12-slim as compiler
ENV PYTHONUNBUFFERED=1
WORKDIR /app/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -Ur requirements.txt

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim as runner
WORKDIR /app/

# 1. Install standard system utilities
RUN apt-get update && apt-get install -y \
    tree \
    && rm -rf /var/lib/apt/lists/*


# 2. Copy the compiled Python virtual environment from stage 1
COPY --from=compiler /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Inform Playwright exactly where to store browser binaries
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
RUN /opt/venv/bin/python -m playwright install chromium
RUN /opt/venv/bin/python -m playwright install-deps chromium

# 4. Copy application code
COPY ./main.py /app/main.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
