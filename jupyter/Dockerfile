# --- Stage 1: Build virtual environment ---
FROM python:3.12-slim as compiler
ENV PYTHONUNBUFFERED=1
WORKDIR /app/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -Ur requirements.txt

CMD ["jupyter", "lab", "--allow-root", "--ip=0.0.0.0", "--port=8080", "--no-browser"]
