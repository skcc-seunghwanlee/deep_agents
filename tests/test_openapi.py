import pytest

pytest.importorskip("fastapi")

from sample_agents.app import create_app
from sample_agents.config import Settings


def test_openapi_schema_is_available_without_forward_ref_error():
    app = create_app(Settings(model_provider="fake", model_name="fake", database_url="memory"))

    schema = app.openapi()

    assert schema["info"]["title"]
    assert "/threads" in schema["paths"]
