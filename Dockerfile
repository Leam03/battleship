FROM ghcr.io/astral-sh/uv:0.12.19 AS uv
FROM python:3.12-slim AS base
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./

FROM base AS test
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen
CMD ["pytest", "--cov", "--cov-report=term-missing"]

FROM base AS build
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
RUN groupadd --system app && useradd --system --gid app app
COPY --from=build /app/.venv ./.venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY examples ./examples
USER app
EXPOSE 8000
CMD ["uvicorn", "battleship.main:app", "--host", "0.0.0.0", "--port", "8000"]
