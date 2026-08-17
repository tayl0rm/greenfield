FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache \
    curl \
    jq \
    coreutils \
    zip

COPY src/bot.py ./bot.py

RUN python3 -m pip install \
    discord \
    python-dotenv \
    google-api-core \
    google-api-python-client \
    google-cloud-compute \
    google-cloud-secret-manager

CMD ["python", "bot.py"]