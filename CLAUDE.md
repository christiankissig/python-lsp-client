# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run a single test
poetry run pytest tests/test_client.py::test_send_request_headers

# Run tests with coverage
poetry run pytest --cov=lsp_client --cov-report=term-missing

# Lint and format checks
poetry run ruff check .
poetry run ruff format --check .

# Type checking
poetry run mypy .

# Auto-fix imports/formatting
poetry run ruff check --fix .
poetry run ruff format .

# Build the package
poetry build
```

## Architecture

The library provides an async LSP client over stdio. There are three modules:

- **`lsp_client/protocol.py`** — Pydantic models for LSP messages. `BaseRequest` is the root model (jsonrpc, id, method, params). Concrete request types (e.g. `InitializeRequest`, `TextDocumentDidOpenRequest`) subclass it and hard-code the `method` field in `__init__`. ID assignment is intentionally not done here — IDs must be supplied by the caller.

- **`lsp_client/client.py`** — `LSPClient` owns the `asyncio.StreamWriter`/`asyncio.StreamReader` pair connected to an LSP server subprocess. It manages request ID allocation (`_allocate_request_id`), serializes requests as LSP framed messages (Content-Length + Content-Type headers + JSON body), and dispatches incoming responses to a user-supplied async `response_handler` callable. The `listen()` method runs the read loop until cancelled.

- **`lsp_client/utils.py`** — `parse_content_type()` parses LSP `Content-Type` headers and returns `(mime_type, encoding)`. Raises `ValueError` for unsupported MIME types and `EncodingError` for unknown charsets. Default encoding is UTF-8, default MIME type is `application/vscode-jsonrpc`.

### Key design decisions

- Request IDs are managed centrally in `LSPClient` (via `build_request()`), not in the protocol models, to avoid global mutable state in `protocol.py`.
- `LSPClient` accepts any async callable as `response_handler`, making it easy to plug in custom dispatch logic without subclassing.
- Protocol models use Pydantic v2 (`model_dump()`, `BaseModel`). The spec reference is LSP 3.17.
- `ruff` is configured with `select = ["I"]` (isort rules only); `black` is the formatter.
