FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY backend/app /app/app
COPY backend/requirements.txt /app/requirements.txt
COPY models /models
COPY backend/entry_point.sh /usr/local/bin/entry_point.sh

RUN chmod +x /usr/local/bin/entry_point.sh

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
