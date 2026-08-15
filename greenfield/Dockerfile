FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache \
    curl \
    jq \
    coreutils \
    zip

COPY src/bot.py ./bot.py

RUN pip install --no-cache-dir \
    discord \
    python-dotenv \
    google-api-core \
    google-api-python-client \
    google-cloud-compute

CMD ["python", "bot.py"]