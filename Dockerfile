FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY README.md .
COPY logger.py .
COPY tests/dummy_data/automated_reporting ./tests/dummy_data/automated_reporting
COPY onboard_system ./onboard_system

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "onboard_system/automated_reporting/generate_daily_report.py", "--use_dummy_data"]