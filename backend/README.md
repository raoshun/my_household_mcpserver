# Backend (Python) – Household Budget Analysis MCP Server

This package contains the Python backend (MCP server, HTTP API, analytics).

## Quick start (from backend/)

- Install deps (using uv):
  - uv sync
- Install optional extras for HTTP API/DB/visualization:
  - VS Code task: "Install Web/Streaming Extras"
  - or: uv pip install -e .[web,streaming,visualization,db]
- Run tests:
  - uv run pytest -v
- Start HTTP API (dev):
  - uv run uvicorn household_mcp.web.http_server:create_http_app --factory --reload --host 0.0.0.0 --port 8000

## Notes

- Data directory is at ../data by default (configurable).
- This folder is migrated from repository root (src/, tests/, pyproject.toml).
