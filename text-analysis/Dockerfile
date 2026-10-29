FROM python:3.13.17-slim-trixie AS phase1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./text-analysis/requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download en_core_web_sm \
    && python -m nltk.downloader -d /nltk_data punkt_tab

ENV NLTK_DATA=/nltk_data


FROM phase1 AS phase2


COPY ./text-analysis/app/ .

COPY ./contracts/ /tmp/contracts/
RUN python -m pip install --no-cache-dir /tmp/contracts

COPY ./observability/ /tmp/observability/
RUN python -m pip install --no-cache-dir /tmp/observability

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

