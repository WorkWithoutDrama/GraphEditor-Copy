# MVP Orchestrator

Minimal glue layer that runs the full ingestion pipeline end-to-end:
**file -> Docling parse -> chunk -> LLM extract -> persist -> Qdrant embed**.

## Quick Start

1. Use the project virtual environment:
   ```bash
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

2. Ensure Ollama is running with `llama3.2` and `nomic-embed-text`:
   ```bash
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```

3. Start Qdrant (e.g. `docker-compose up -d qdrant`).

4. Copy `.env.example` to `.env` and set `LLM_GEMINI_ENABLED=false` for Ollama-only.

5. Run migrations:
   ```bash
   alembic upgrade head
   ```

6. Ingest a file:
   ```bash
   python -m app.orchestrator.cli ingest --workspace ws1 path/to/file.pdf
   ```

7. Inspect results:
   ```bash
   python -m app.orchestrator.cli inspect --run <run_id>
   ```

## Commands

Use the project `.venv` (activate it first, or run `.venv/Scripts/python.exe -m ...` on Windows, `.venv/bin/python -m ...` on Linux/macOS).

- **ingest** — Parse, chunk, LLM extract, embed, persist to SQL + Qdrant
- **inspect** — Show run status and sample extraction JSON

## Options

- `--force` — Reprocess all chunks (ignore existing DONE run)
- `--workspace` — Workspace name (default: ws1)
