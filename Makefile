# Makefile for CSV Normalizer Utility
# 
# This Makefile provides installation and management targets for the CSV normalizer utility

# Installation directories
PREFIX ?= /usr/local
BINDIR = $(PREFIX)/bin
SCRIPTDIR = $(CURDIR)/script
SCRIPT_NAME = prepare.sh
TARGET_NAME = csv_normalizer

# Python requirements
PYTHON_DEPS = chardet duckdb

# DuckDB CLI download URL (latest version)
DUCKDB_VERSION = v1.1.3
DUCKDB_URL = https://github.com/duckdb/duckdb/releases/download/$(DUCKDB_VERSION)/duckdb_cli-linux-amd64.zip

.PHONY: all install uninstall test clean check help

# Default target
all: help

# Install the utility
install: check-python install-duckdb
	@echo "Installing CSV Normalizer Utility..."
	@echo "Installing Python dependencies..."
	pip3 install $(PYTHON_DEPS)
	@echo "Installing script to $(BINDIR)/$(TARGET_NAME)..."
	@mkdir -p $(BINDIR)
	@cp $(SCRIPTDIR)/$(SCRIPT_NAME) $(BINDIR)/$(TARGET_NAME)
	@chmod +x $(BINDIR)/$(TARGET_NAME)
	@echo "Installation complete!"
	@echo "You can now use 'csv_normalizer' command globally"

# Install DuckDB CLI tool
install-duckdb:
	@echo "Installing DuckDB CLI tool..."
	@if ! command -v duckdb >/dev/null 2>&1; then \
		echo "Downloading DuckDB CLI..."; \
		mkdir -p /tmp/duckdb-install; \
		cd /tmp/duckdb-install && \
		curl -L $(DUCKDB_URL) -o duckdb_cli.zip && \
		unzip -q duckdb_cli.zip && \
		mkdir -p $(BINDIR) && \
		cp duckdb $(BINDIR)/ && \
		chmod +x $(BINDIR)/duckdb && \
		rm -rf /tmp/duckdb-install && \
		echo "DuckDB CLI installed to $(BINDIR)/duckdb"; \
	else \
		echo "DuckDB CLI already available"; \
	fi

# Uninstall the utility
uninstall:
	@echo "Uninstalling CSV Normalizer Utility..."
	@if [ -f "$(BINDIR)/$(TARGET_NAME)" ]; then \
		rm -f $(BINDIR)/$(TARGET_NAME); \
		echo "Removed $(BINDIR)/$(TARGET_NAME)"; \
	else \
		echo "$(TARGET_NAME) not found in $(BINDIR)"; \
	fi
	@if [ -f "$(BINDIR)/duckdb" ]; then \
		rm -f $(BINDIR)/duckdb; \
		echo "Removed $(BINDIR)/duckdb"; \
	fi
	@echo "Note: Python dependencies ($(PYTHON_DEPS)) were not removed"
	@echo "Uninstall complete!"

# Run tests
test:
	@echo "Running tests..."
	@if [ -f "$(SCRIPTDIR)/$(SCRIPT_NAME)" ]; then \
		echo "Testing script syntax..."; \
		bash -n $(SCRIPTDIR)/$(SCRIPT_NAME) && echo "Script syntax OK"; \
	fi
	@if [ -d "test" ] && [ -n "$$(ls -A test 2>/dev/null)" ]; then \
		echo "Running test files..."; \
		for test_file in test/*.csv; do \
			if [ -f "$$test_file" ]; then \
				echo "Testing with: $$test_file"; \
				$(SCRIPTDIR)/$(SCRIPT_NAME) "$$test_file" --output-dir /tmp/csv_test_output; \
			fi; \
		done; \
		rm -rf /tmp/csv_test_output; \
	else \
		echo "No test files found in test directory"; \
	fi

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	@find . -name "*.csv~" -delete 2>/dev/null || true
	@find . -name ".DS_Store" -delete 2>/dev/null || true
	@rm -rf tmp/ 2>/dev/null || true
	@rm -rf /tmp/csv_test_output 2>/dev/null || true
	@echo "Clean complete!"

# Check dependencies
check: check-python check-system-deps
	@echo "All dependency checks passed!"

check-python:
	@echo "Checking Python installation..."
	@command -v python3 >/dev/null 2>&1 || (echo "Error: python3 is required but not installed" && exit 1)
	@echo "Python3 found: $$(python3 --version)"

check-system-deps:
	@echo "Checking system dependencies..."
	@command -v iconv >/dev/null 2>&1 || (echo "Error: iconv is required but not installed" && exit 1)
	@echo "iconv found"
	@command -v file >/dev/null 2>&1 || (echo "Error: file command is required but not installed" && exit 1)
	@echo "file command found"
	@command -v curl >/dev/null 2>&1 || (echo "Error: curl is required for downloading DuckDB but not installed" && exit 1)
	@echo "curl found"
	@command -v unzip >/dev/null 2>&1 || (echo "Error: unzip is required for extracting DuckDB but not installed" && exit 1)
	@echo "unzip found"

# Show help
help:
	@echo "CSV Normalizer Utility - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install     Install the utility and its dependencies"
	@echo "  uninstall   Remove the installed utility"
	@echo "  test        Run tests to verify the utility works"
	@echo "  clean       Remove temporary files"
	@echo "  check       Check if all dependencies are installed"
	@echo "  help        Show this help message"
	@echo ""
	@echo "Installation options:"
	@echo "  PREFIX      Installation prefix (default: /usr/local)"
	@echo "              Example: make install PREFIX=/opt/local"
	@echo ""
	@echo "Examples:"
	@echo "  make install                    # Install to /usr/local/bin"
	@echo "  make install PREFIX=~/.local   # Install to ~/.local/bin"
	@echo "  make check                      # Verify dependencies"
	@echo "  make test                       # Run tests"
	@echo "  make uninstall                  # Remove installation"