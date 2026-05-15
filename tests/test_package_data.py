import tomllib
from pathlib import Path


def test_schema_sql_is_declared_as_package_data():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["tool"]["setuptools"]["package-data"]["sample_agents.persistence"] == ["schema.sql"]


def test_missing_langchain_extra_raises_actionable_runtime_error(monkeypatch):
    from sample_agents.config import Settings
    from sample_agents.integrations import models

    def fake_find_spec(name):
        if name == "langchain":
            return None
        raise AssertionError(f"unexpected lookup: {name}")

    monkeypatch.setattr(models.importlib.util, "find_spec", fake_find_spec)

    try:
        models.create_chat_model(Settings(model_provider="openai", openai_api_key="test-key"))
    except RuntimeError as exc:
        assert "requires optional LangChain dependencies" in str(exc)
        assert "MODEL_PROVIDER=fake" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing langchain extra")
