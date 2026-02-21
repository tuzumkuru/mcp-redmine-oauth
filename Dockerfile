# Builder: install package and dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Runtime image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 appuser

# Copy installed packages and entry point script from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

USER appuser

EXPOSE 8000

CMD ["mcp-redmine-oauth"]
