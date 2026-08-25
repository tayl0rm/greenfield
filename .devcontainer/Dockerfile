FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /workspaces/app

ENV PATH="/workspaces/app/.venv/bin:$PATH"

RUN if [ -f pyproject.toml ]; then uv sync --frozen; fi