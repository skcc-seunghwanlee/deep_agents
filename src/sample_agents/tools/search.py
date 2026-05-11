from __future__ import annotations

from sample_agents.integrations.search_providers import SearchProvider, SearchResult


class SearchReferenceTool:
    name = "search_reference"

    def __init__(self, provider: SearchProvider) -> None:
        self.provider = provider

    def __call__(self, query: str) -> list[SearchResult]:
        return self.provider.search(query)
