# ===== Build stage =====
FROM python:3.13-slim AS builder

WORKDIR /app

# Build deps (можно оставить, если реально нужны)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (если используешь)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY uv.lock pyproject.toml ./
COPY requirements.txt .

# ===== Runtime stage =====
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Runtime deps
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

#  ФИКСЫ (главное)
RUN useradd -m -u 1000 appuser && \
    sed -i 's/\r$//' /app/scripts/entrypoint.sh && \
    chmod 755 /app/scripts/entrypoint.sh && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000

#  запускаем через bash (устраняет 90% проблем)
ENTRYPOINT ["bash", "/app/scripts/entrypoint.sh"]