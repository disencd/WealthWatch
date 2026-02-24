# Stage 1 – Build SvelteKit frontend
FROM node:22-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2 – Install Python dependencies
FROM python:3.12-slim AS builder

WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

# Final stage
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages
COPY --from=builder /install/deps /usr/local

# Copy application code
COPY app/ ./app/

# Copy SvelteKit build output as the web directory
COPY --from=frontend-builder /frontend/build ./web/

# Keep legacy web/ as fallback (if needed)
# COPY web/ ./web-legacy/

# Create receipts directory
RUN mkdir -p /app/receipts && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
