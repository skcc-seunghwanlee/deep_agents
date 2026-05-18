from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from typing import Any

from sample_agents.config import Settings, validate_settings


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    name: str
    mode: str


class FakeChatModel:
    def __init__(self, name: str = "fake") -> None:
        self.name = name


def model_info(settings: Settings) -> ModelInfo:
    mode = "local" if settings.model_provider == "ollama" else "remote-api"
    if settings.model_provider == "fake":
        mode = "offline-fake"
    return ModelInfo(provider=settings.model_provider, name=settings.model_name, mode=mode)


def create_chat_model(settings: Settings) -> Any:
    validate_settings(settings)
    if settings.model_provider == "fake":
        return FakeChatModel(settings.model_name)

    module = _load_langchain_chat_models(settings.model_provider)
    if settings.model_provider == "openai":
        return module.init_chat_model(f"openai:{settings.model_name}")
    if settings.model_provider == "ollama":
        return module.init_chat_model(f"ollama:{settings.model_name}", base_url=settings.ollama_base_url)

    raise RuntimeError(
        f"Provider {settings.model_provider!r} requires optional model dependencies. "
        "Install the matching extra or use MODEL_PROVIDER=fake."
    )


def _load_langchain_chat_models(provider: str) -> Any:
    try:
        if importlib.util.find_spec("langchain") is None:
            raise ModuleNotFoundError("langchain")
        if importlib.util.find_spec("langchain.chat_models") is None:
            raise ModuleNotFoundError("langchain.chat_models")
        return importlib.import_module("langchain.chat_models")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Provider {provider!r} requires optional LangChain dependencies. "
            "Install the matching extra or use MODEL_PROVIDER=fake."
        ) from exc
