from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchResult:
    title: str
    snippet: str
    source: str
    score: float = 1.0


class SearchProvider(Protocol):
    def search(self, query: str) -> list[SearchResult]: ...


class MockSearchProvider:
    def search(self, query: str) -> list[SearchResult]:
        return [
            SearchResult(
                title="Mock privacy guidance",
                snippet="개인정보, 보관 기간, 제3자 제공 고지는 명확한 근거와 고객 안내가 필요합니다.",
                source="mock://privacy-guidance",
                score=0.91,
            ),
            SearchResult(
                title="Mock customer communication checklist",
                snippet="고객 답변은 확정적 법률 판단을 피하고 확인 가능한 문서 근거를 분리해 작성합니다.",
                source="mock://customer-reply-checklist",
                score=0.84,
            ),
        ]


def create_search_provider(name: str) -> SearchProvider:
    if name == "mock":
        return MockSearchProvider()
    raise ValueError("Only SEARCH_PROVIDER=mock is implemented; add Web/RAG/MCP providers behind SearchProvider.")
