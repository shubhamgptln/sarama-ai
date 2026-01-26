.PHONY: help build run test clean docker-build docker-run lint fmt

# Variables
APP_NAME=sarama-ai
DOCKER_IMAGE=$(APP_NAME):latest
MAIN_PATH=./cmd/main.go
GO=go

help: ## Display this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the application
	@echo "Building $(APP_NAME)..."
	$(GO) build -o bin/$(APP_NAME) $(MAIN_PATH)
	@echo "Build complete: bin/$(APP_NAME)"

run: build ## Build and run the application
	@echo "Running $(APP_NAME)..."
	./bin/$(APP_NAME)

test: ## Run all tests
	@echo "Running tests..."
	$(GO) test -v ./...

test-coverage: ## Run tests with coverage
	@echo "Running tests with coverage..."
	$(GO) test -v -coverprofile=coverage.out ./...
	$(GO) tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report: coverage.html"

clean: ## Clean build artifacts
	@echo "Cleaning..."
	$(GO) clean
	rm -f bin/$(APP_NAME)
	rm -f coverage.out coverage.html

lint: ## Run linter
	@echo "Running linter..."
	golangci-lint run ./...

fmt: ## Format code
	@echo "Formatting code..."
	$(GO) fmt ./...

deps: ## Download dependencies
	@echo "Downloading dependencies..."
	$(GO) mod download
	$(GO) mod tidy

docker-build: ## Build Docker image
	@echo "Building Docker image: $(DOCKER_IMAGE)"
	docker build -t $(DOCKER_IMAGE) .

docker-run: docker-build ## Build and run Docker container
	@echo "Running Docker container..."
	docker run --rm -p 8080:8080 $(DOCKER_IMAGE)

docker-push: docker-build ## Push Docker image to registry
	@echo "Pushing $(DOCKER_IMAGE) to registry..."
	docker push $(DOCKER_IMAGE)

install-tools: ## Install development tools
	@echo "Installing development tools..."
	$(GO) install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

all: clean fmt lint test build ## Run all steps (clean, fmt, lint, test, build)
