# Prompt Royale — Backend Service

FastAPI-powered backend service for **Prompt Royale (College Academic AI Platform)**.

## Architecture

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL with `pgvector`
- **Core Capabilities:**
  - Subject-based access control (SBAC)
  - Document ingestion, chunking, and embedding
  - Grounded RAG query pipeline with citations
  - Quiz Battle question generator and session state
  - Multi-tenant college isolation

## Setup & Testing

```bash
# Install dependencies
pip install -e ".[test]"

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --port 8000
```

## Contributing & SDLC

This repository is maintained via the autonomous SDLC agent workflow described in root `AGENTS.md`. All feature development takes place in isolated `git worktrees`, requires unit tests, updates `CHANGELOG.md`, and is submitted via Pull Request.
