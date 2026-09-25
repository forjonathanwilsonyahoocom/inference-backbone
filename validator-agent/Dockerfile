FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY ./validator-agent/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -Ur requirements.txt

COPY ./validator-agent/main.py /app/main.py
COPY ./contracts/ /tmp/contracts/
RUN pip install --no-cache-dir /tmp/contracts
COPY ./observability/ /tmp/observability/
RUN pip install --no-cache-dir /tmp/observability

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
