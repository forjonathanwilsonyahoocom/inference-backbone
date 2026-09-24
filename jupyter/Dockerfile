# --- Stage 1: Build virtual environment ---
FROM python:3.12-slim AS compiler
ENV PYTHONUNBUFFERED=1
WORKDIR /app/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -Ur requirements.txt

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim AS runner
WORKDIR /app/

# 1. Copy the compiled Python virtual environment from stage 1
COPY --from=compiler /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 2. Set up the local runtime workspace
RUN mkdir -p /localjup/notebooks
WORKDIR /localjup/notebooks
ENV PYTHONPATH=/localjup/notebooks:/localjup/notebooks/app

EXPOSE 8080

CMD ["jupyter", "lab", "--allow-root", "--ip=0.0.0.0", "--port=8080", "--no-browser"]
