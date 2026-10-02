# Task interface for GNU Make 3.81+ and a POSIX shell.
.DEFAULT_GOAL := help

CLI_DIR := cli
KEYWORDS_DIR := skills/google-keyword-research

.PHONY: help cli-build test cli-test keywords-test check cli-vet cli-lint cli-release-check

help:
	@printf '%s\n' \
		'Usage: make <target>' \
		'  help               Show available targets (default)' \
		'  cli-build          Build cli/bin/dev/coreskills from local source' \
		'  test               Run CLI and keyword research tests' \
		'  cli-test           Run Go tests' \
		'  keywords-test      Run Python tests; uv may download dependencies' \
		'  check              Run CLI CI checks (requires lint and release tools)' \
		'  cli-vet            Run go vet' \
		'  cli-lint           Run golangci-lint' \
		'  cli-release-check  Validate GoReleaser configuration'

cli-build:
	cd "$(CLI_DIR)" && go build -o bin/dev/coreskills ./cmd/coreskills

test: cli-test keywords-test

cli-test:
	cd "$(CLI_DIR)" && go test ./...

keywords-test:
	cd "$(KEYWORDS_DIR)" && uv run --with 'google-ads>=32,<33' python -m unittest discover -s tests -v

check: cli-test cli-vet cli-lint cli-release-check

cli-vet:
	cd "$(CLI_DIR)" && go vet ./...

cli-lint:
	cd "$(CLI_DIR)" && golangci-lint run

cli-release-check:
	cd "$(CLI_DIR)" && goreleaser check
