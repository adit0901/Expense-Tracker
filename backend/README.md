# FinTrack backend

FastAPI + SQLAlchemy 2 + PostgreSQL. Managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run ruff check . && uv run mypy && uv run pytest
uv run uvicorn app.main:app --reload
```
