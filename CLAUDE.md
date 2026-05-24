# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SecurePipe is a multi-tool security scanning platform. It exposes a REST API that runs four security scanners in parallel against a local codebase path and aggregates their results.

- **Scanner service**: `scanner/` — Python/FastAPI app (port 8001)
- **Example target**: `repos/task-manager/` — a Laravel 13 app used as a test subject for scans

## Running the Scanner

```bash
# Start the scanner service
docker-compose up scanner

# Rebuild after code changes
docker-compose up --build scanner
```

The scanner runs on `http://localhost:8001`. Sample HTTP requests are in `securepipe.http`.

## Scanner API

```
GET  /health        — health check
POST /scan          — run all scanners against a repo path
                      body: { "repo_path": "task-manager" }
```

Paths in `repo_path` are resolved relative to `/repos` inside the container (mapped from `./repos` on the host).

## Architecture

The scanner (`scanner/main.py`) is a single FastAPI app. On `POST /scan` it:

1. Validates the repo path exists inside `/repos`
2. Runs four security tools concurrently via `asyncio.gather`:
   - **Semgrep** — SAST, detects code pattern vulnerabilities
   - **Trivy** — package and filesystem vulnerability scanning
   - **Gitleaks** — secret/credential detection in git history
   - **Checkov** — IaC scanning (Terraform, CloudFormation, Dockerfiles)
3. Returns a combined JSON object with results from all four scanners

Each scanner runs as a subprocess and its stdout/stderr are captured. Failures are caught individually so one scanner failing doesn't block the rest.

## Adding a New Scanner

To add a fifth scanner, follow the pattern in `scanner/main.py`:
- Write an `async def run_<toolname>(repo_path)` function that runs a subprocess and returns parsed JSON
- Add it to the `asyncio.gather()` call in the `/scan` endpoint handler
- Install the tool in `scanner/Dockerfile`

## Task-Manager (Test Target)

The `repos/task-manager/` project has its own `CLAUDE.md` at `repos/task-manager/project/CLAUDE.md` covering its commands, DDD/CQRS architecture, and test strategy. Refer to it when working on that subproject.

Key commands for the task-manager:
```bash
composer run setup    # one-time setup
composer run dev      # start dev server + queue + Vite
composer run test     # run all Pest tests
./vendor/bin/behat    # run BDD scenarios
./vendor/bin/deptrac  # validate architecture layer boundaries
```