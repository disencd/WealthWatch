.PHONY: help build run test clean deps setup

# Default target
help:
	@echo "Available commands:"
	@echo "  setup    - Install dependencies and setup environment"
	@echo "  deps     - Install Go dependencies"
	@echo "  build    - Build the application"
	@echo "  run      - Run the application"
	@echo "  test     - Run tests"
	@echo "  clean    - Clean build artifacts"
	@echo "  fmt      - Format Go code"
	@echo "  lint     - Run linter"

# Install dependencies and setup environment
setup:
	@echo "Setting up WealthWatch..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file from template"; fi
	@make deps
	@echo "Setup complete! Please edit .env file with your database configuration."

# Install Go dependencies
deps:
	@echo "Installing Go dependencies..."
	go mod download
	go mod tidy

# Build the application
build:
	@echo "Building WealthWatch..."
	go build -o bin/wealthwatch main.go

# Run the application
run:
	@echo "Starting WealthWatch..."
	go run main.go

# Run tests
test:
	@echo "Running tests..."
	go test -v ./...

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf bin/
	go clean

# Format Go code
fmt:
	@echo "Formatting Go code..."
	go fmt ./...

# Run linter (requires golangci-lint)
lint:
	@echo "Running linter..."
	@if command -v golangci-lint > /dev/null 2>&1; then \
		golangci-lint run; \
	else \
		echo "golangci-lint not installed. Install with: curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b \$$(go env GOPATH)/bin v1.54.2"; \
	fi

# Development mode with hot reload (requires air)
dev:
	@echo "Starting development server with hot reload..."
	@if command -v air > /dev/null 2>&1; then \
		air; \
	else \
		echo "air not installed. Install with: go install github.com/cosmtrek/air@latest"; \
		make run; \
	fi

# Generate migration files (if needed)
migrate:
	@echo "Running database migrations..."
	go run main.go

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t wealthwatch:latest .

# Run with Docker
docker-run:
	@echo "Running with Docker..."
	docker run -p 8080:8080 --env-file .env wealthwatch:latest
