FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache \
    curl \
    jq \
    coreutils \
    zip

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/

CMD ["python", "src/bot.py"]