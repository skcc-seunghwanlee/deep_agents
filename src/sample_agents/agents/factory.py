from __future__ import annotations

import importlib
import importlib.util
import inspect
from typing import Any

from sample_agents.agents.prompts import DOCUMENT_REVIEW_INSTRUCTIONS
from sample_agents.agents.subagents import DOCUMENT_READER, RISK_REVIEWER
from sample_agents.config import Settings
from sample_agents.integrations.models import FakeChatModel, create_chat_model


class DeepAgentFactory:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self, tools: list[Any] | None = None) -> Any:
        model = create_chat_model(self.settings)
        if isinstance(model, FakeChatModel):
            return model
        if importlib.util.find_spec("deepagents") is not None:
            module = importlib.import_module("deepagents")
            create_fn = module.create_deep_agent
            signature = inspect.signature(create_fn)
            kwargs: dict[str, Any] = {"model": model, "tools": tools or []}

            if "instructions" in signature.parameters:
                kwargs["instructions"] = DOCUMENT_REVIEW_INSTRUCTIONS
            elif "system_prompt" in signature.parameters:
                kwargs["system_prompt"] = DOCUMENT_REVIEW_INSTRUCTIONS
            elif "prompt" in signature.parameters:
                kwargs["prompt"] = DOCUMENT_REVIEW_INSTRUCTIONS

            if "subagents" in signature.parameters:
                kwargs["subagents"] = [DOCUMENT_READER, RISK_REVIEWER]
            elif "agents" in signature.parameters:
                kwargs["agents"] = [DOCUMENT_READER, RISK_REVIEWER]

            return create_fn(**kwargs)
        raise RuntimeError("deepagents is not installed. Install the openai/ollama extra or use MODEL_PROVIDER=fake.")
