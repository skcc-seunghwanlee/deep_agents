import tomllib
from pathlib import Path


def test_schema_sql_is_declared_as_package_data():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["tool"]["setuptools"]["package-data"]["sample_agents.persistence"] == ["schema.sql"]
