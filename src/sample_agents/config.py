from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Deep Agents FastAPI Sample"
    debug: bool = False
    model_provider: str = "fake"
    model_name: str = "fake-document-reviewer"
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    search_provider: str = "mock"
    database_url: str = "sqlite:///./deep_agents_demo.db"
    storage_backend: str = "local"
    local_storage_dir: Path = Path(".local_storage")

    @property
    def is_fake_model(self) -> bool:
        return self.model_provider == "fake"


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    _load_dotenv()
    return Settings(
        app_name=os.getenv("APP_NAME", "Deep Agents FastAPI Sample"),
        debug=_bool(os.getenv("DEBUG"), False),
        model_provider=os.getenv("MODEL_PROVIDER", "fake").strip().lower(),
        model_name=os.getenv("MODEL_NAME", "fake-document-reviewer"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        search_provider=os.getenv("SEARCH_PROVIDER", "mock").strip().lower(),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./deep_agents_demo.db"),
        storage_backend=os.getenv("STORAGE_BACKEND", "local").strip().lower(),
        local_storage_dir=Path(os.getenv("LOCAL_STORAGE_DIR", ".local_storage")),
    )


def validate_settings(settings: Settings) -> None:
    if settings.model_provider not in {"openai", "ollama", "fake"}:
        raise ValueError("MODEL_PROVIDER must be one of: openai, ollama, fake")
    if settings.model_provider == "openai" and not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is required when MODEL_PROVIDER=openai. "
            "Set OPENAI_API_KEY, switch to MODEL_PROVIDER=ollama for local Ollama, "
            "or use MODEL_PROVIDER=fake to exercise the API without an LLM."
        )
    if settings.storage_backend != "local":
        raise ValueError("Only STORAGE_BACKEND=local is implemented in this sample.")
