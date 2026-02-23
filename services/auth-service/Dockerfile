FROM golang:1.21-bookworm AS builder

ARG GOPROXY=https://proxy.golang.org,direct
ARG GOSUMDB=off
ENV GOPROXY=$GOPROXY \
    GOSUMDB=$GOSUMDB

# Set working directory
WORKDIR /app

# Copy go module files (go.sum may not exist)
COPY go.* ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o auth-service main.go

# Production stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates tzdata curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -m -s /usr/sbin/nologin appuser

# Set working directory
WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/auth-service .

# Create necessary directories
RUN mkdir -p /app/tmp && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["./auth-service"]
