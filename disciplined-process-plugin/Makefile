# Makefile for disciplined-process plugin hooks
GO := go
GOFLAGS := -ldflags="-s -w" -trimpath

CMDS := trace-validator coverage-check adr-validator phase-emitter

PLATFORMS := darwin/arm64 darwin/amd64 linux/amd64 linux/arm64 windows/amd64

.PHONY: all dev clean test lint help

dev:
	@mkdir -p bin
	@for cmd in $(CMDS); do \
		if [ -d "cmd/$$cmd" ]; then \
			echo "Building $$cmd..."; \
			$(GO) build $(GOFLAGS) -o bin/$$cmd ./cmd/$$cmd; \
		fi; \
	done
	@echo "Built binaries in bin/"
	@ls -la bin/

all:
	@mkdir -p bin
	@for cmd in $(CMDS); do \
		if [ -d "cmd/$$cmd" ]; then \
			echo "Building $$cmd for all platforms..."; \
			GOOS=darwin GOARCH=arm64 CGO_ENABLED=0 $(GO) build $(GOFLAGS) -o bin/$$cmd-darwin-arm64 ./cmd/$$cmd; \
			GOOS=darwin GOARCH=amd64 CGO_ENABLED=0 $(GO) build $(GOFLAGS) -o bin/$$cmd-darwin-amd64 ./cmd/$$cmd; \
			GOOS=linux GOARCH=amd64 CGO_ENABLED=0 $(GO) build $(GOFLAGS) -o bin/$$cmd-linux-amd64 ./cmd/$$cmd; \
			GOOS=linux GOARCH=arm64 CGO_ENABLED=0 $(GO) build $(GOFLAGS) -o bin/$$cmd-linux-arm64 ./cmd/$$cmd; \
			GOOS=windows GOARCH=amd64 CGO_ENABLED=0 $(GO) build $(GOFLAGS) -o bin/$$cmd-windows-amd64.exe ./cmd/$$cmd; \
		fi; \
	done
	@echo "Built binaries:"
	@ls -la bin/

test:
	$(GO) test -v -race ./...

lint:
	@command -v golangci-lint >/dev/null 2>&1 || { echo "Install: go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"; exit 1; }
	golangci-lint run ./...

clean:
	rm -rf bin/

install-tools:
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

help:
	@echo "Available targets:"
	@echo "  dev          - Build for current platform (fast)"
	@echo "  all          - Build for all platforms"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linter"
	@echo "  clean        - Remove built binaries"
	@echo "  install-tools - Install development tools"
	@echo ""
	@echo "Commands being built: $(CMDS)"
