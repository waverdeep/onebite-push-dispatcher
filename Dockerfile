# syntax=docker/dockerfile:1

# --- Stage 1: builder (install dependencies with uv) ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies first (cached unless lockfile/pyproject changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY app ./app
COPY job_main.py ./
RUN uv sync --frozen --no-dev

# --- Stage 2: runtime ---
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Bring in the prebuilt virtualenv and application code
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/job_main.py /app/job_main.py
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

USER app

# Cloud Run Job entrypoint. Runs to completion; exit 0 = success.
# Defaults to the current KST hour as the send slot. Override at execution time
# with --args 14 or by setting the PUSH_HOUR env var (local testing).
ENTRYPOINT ["python", "job_main.py"]
