# Stage 1: Install dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy project manifest and install only dependencies.
# A stub src/ dir is needed for setuptools package discovery.
COPY pyproject.toml .
RUN mkdir src && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Runtime image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ ./src/

USER appuser

EXPOSE 8000

CMD ["python", "src/server.py"]
