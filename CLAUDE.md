# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

py-http-auto-test is a Python library for HTTP automated testing using YAML test specifications. It supports both standalone execution and pytest integration. The library uses libcurl/pycurl for HTTP requests and supports websockets testing.

## Key Commands

### Testing
- `pytest -v test` - Run the test suite
- `pytest -v ./test --capture=no` - Run tests with output capture disabled
- `make test` - Run tests using Makefile

### Development
- `isort .` - Sort imports (line length 120)
- `black -l 120 .` - Format code with Black (line length 120)
- `pre-commit run --all-files` - Run pre-commit hooks

### Building and Release
- `make clean` - Remove build artifacts
- `make dist` - Build source and wheel distributions
- `twine check dist/*.whl` - Validate built packages
- `make release` - Run tests, build, and publish to PyPI

### Running HTTP Tests
- `http-test-runner.py --test-file example.yaml` - Run YAML test files standalone
- `http-test-runner.py --test-file test.yaml --target-host 127.0.0.1` - Run against alternative host
- `http-test-runner.py --test-file test.yaml --var "hostname=test.example.com"` - Use template variables
- `pytest -v ./test.yaml` - Run YAML tests with pytest
- `HTTPTEST_TARGET_HOST="127.0.0.1" pytest -v ./test.yaml` - Pass environment variables to pytest

## Architecture

### Core Components

- **`http_test/spec.py`** - Main test specification parser and runner logic
- **`http_test/request.py`** - HTTP request handling using pycurl
- **`http_test/ws_request.py`** - WebSocket request handling
- **`http_test/runner.py`** - Test runner for standalone execution
- **`conftest.py`** - Pytest plugin for YAML test file discovery and execution
- **`bin/http-test-runner.py`** - CLI script for standalone test execution

### Test Structure

Tests are defined in YAML files with this structure:
- `base_url` - Base URL for all requests
- `tests` - Array of test specifications with url, description, headers, match criteria, etc.
- Template variables using Jinja2 syntax (e.g., `{{ hostname }}`) are supported

### Key Features

- HTTP/1.1 and HTTP/2 support
- WebSocket testing capability
- Response matching on status, headers, body content, and timing
- Template variable substitution
- Skip/verbose test options
- Alternative host targeting (similar to curl --connect-to)

## Dependencies

- Python 3.8+ required
- `libcurl4-openssl-dev` system package required for pycurl
- Main dependencies: pycurl, websockets, click, jinja2
- Dev dependencies: pytest, isort, black, setuptools, wheel, twine

## CI/CD

- GitHub Actions runs tests on Python 3.8, 3.12, and 3.13
- Publishes to PyPI on release using Trusted Publishers
- Pre-commit hooks enforce code formatting and basic checks
