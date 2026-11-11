import pytest
from fastapi.testclient import TestClient

from app.core.config import DEV_JWT_SECRET, ConfigurationError, Settings
from app.main import create_app

PROD_DB = "postgresql+psycopg://u:p@db:5432/fintrack"


def test_production_refuses_default_jwt_secret() -> None:
    settings = Settings(app_env="production", jwt_secret=DEV_JWT_SECRET, database_url=PROD_DB)
    with pytest.raises(ConfigurationError, match="JWT_SECRET"):
        create_app(settings)


def test_production_refuses_missing_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(app_env="production", jwt_secret="s" * 40)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        settings.validate_for_runtime()


def test_production_with_valid_secrets_starts_and_hides_docs() -> None:
    app = create_app(Settings(app_env="production", jwt_secret="s" * 40, database_url=PROD_DB))
    client = TestClient(app)
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404


def test_docs_available_in_development() -> None:
    client = TestClient(create_app(Settings(app_env="development")))
    resp = client.get("/api/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()


def test_cors_origins_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://app.example.com")
    assert Settings().cors_origins == ["http://localhost:5173", "https://app.example.com"]
    monkeypatch.setenv("CORS_ORIGINS", '["https://a.example"]')
    assert Settings().cors_origins == ["https://a.example"]


def test_env_example_file_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    example = Path(__file__).resolve().parents[3] / ".env.example"
    for line in example.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            monkeypatch.setenv(key, value)
    settings = Settings()
    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.app_env == "development"
