# --- Stage 1: Build virtual environment ---
FROM python:3.12-slim as compiler
ENV PYTHONUNBUFFERED=1
WORKDIR /app/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install just playwright first — rarely changes, so this layer (and the slow
# browser download below) stays cached across normal requirements.txt edits
RUN pip install --upgrade pip && pip install playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
RUN python -m playwright install chromium

# Now install everything else — this is the layer that actually changes often
COPY ./requirements.txt /app/requirements.txt
RUN pip install -Ur requirements.txt

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim as runner
WORKDIR /app/

RUN apt-get update && apt-get install -y tree && rm -rf /var/lib/apt/lists/*

COPY --from=compiler /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright

RUN python -m playwright install-deps chromium

COPY ./main.py /app/main.py
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
