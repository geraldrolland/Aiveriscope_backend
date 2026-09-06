FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium fonts-liberation supervisor && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip pip install --default-timeout=600 --retries=5 -r /app/backend/requirements.txt

RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('wordnet', quiet=True)"

COPY . .

RUN chmod +x /app/backend/entry_point.sh

ENV PYTHONPATH=/app/backend

EXPOSE 8000

ENTRYPOINT ["/app/backend/entry_point.sh"]
CMD ["supervisord", "-c", "/app/backend/supervisord.conf"]

