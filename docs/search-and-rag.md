# Search and RAG Extension

Agent는 `search_reference` 같은 tool만 알면 됩니다. 실제 구현은 provider 뒤에 숨깁니다.

```text
SearchReferenceTool
  -> SearchProvider
     -> MockSearchProvider
     -> WebSearchProvider
     -> RagSearchProvider
     -> McpSearchProvider
```

MVP는 `MockSearchProvider`를 사용합니다. 실제 프로젝트에서는 사내 RAG API, vector DB, MCP search server를 `SearchProvider.search()` 구현으로 연결하세요.
