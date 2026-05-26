from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentWorkspace:
    files: dict[str, str] = field(default_factory=dict)

    def write(self, path: str, content: str) -> None:
        self.files[self._normalize(path)] = content

    def read(self, path: str) -> str | None:
        return self.files.get(self._normalize(path))

    def list_paths(self) -> list[str]:
        return sorted(self.files)

    def _normalize(self, path: str) -> str:
        normalized = path.strip()
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized


class WorkspaceRegistry:
    def __init__(self) -> None:
        self._workspaces: dict[str, AgentWorkspace] = {}

    def for_thread(self, thread_id: str) -> AgentWorkspace:
        if thread_id not in self._workspaces:
            self._workspaces[thread_id] = AgentWorkspace()
        return self._workspaces[thread_id]

    def reset(self, thread_id: str) -> None:
        self._workspaces.pop(thread_id, None)
