from __future__ import annotations

from dataclasses import replace

from sample_agents.agents.factory import DeepAgentFactory
from sample_agents.config import Settings
from sample_agents.domain.models import AgentResponse, AgentRun, ApprovalRequest, RunStatus, ToolCall, new_id, utc_now
from sample_agents.integrations.models import model_info
from sample_agents.integrations.search_providers import SearchProvider
from sample_agents.persistence.repositories import ConversationRepository
from sample_agents.services.workspace import AgentWorkspace, WorkspaceRegistry


class AgentService:
    def __init__(
        self,
        settings: Settings,
        repository: ConversationRepository,
        workspaces: WorkspaceRegistry,
        search_provider: SearchProvider,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.workspaces = workspaces
        self.search_provider = search_provider

    def run(self, thread_id: str, triggering_message_id: str, user_content: str) -> AgentResponse:
        info = model_info(self.settings)
        run = AgentRun(
            id=new_id("run"),
            thread_id=thread_id,
            triggering_message_id=triggering_message_id,
            status=RunStatus.STARTED,
            model_provider=info.provider,
            model_name=info.name,
        )
        self.repository.save_agent_run(run)
        workspace = self.workspaces.for_thread(thread_id)
        if self.settings.model_provider == "fake":
            response = self._run_fake_document_agent(thread_id, run.id, user_content, workspace)
        else:
            response = self._run_deep_agent(thread_id, user_content, workspace)
        self.repository.update_agent_run(replace(run, status=RunStatus.SUCCEEDED, finished_at=utc_now()))
        return response

    def _run_deep_agent(self, thread_id: str, user_content: str, workspace: AgentWorkspace) -> AgentResponse:
        workspace_context = "\n".join(
            f"{path}:\n{workspace.read(path) or ''}" for path in workspace.list_paths() if path.startswith("/inputs/")
        )
        prompt = (
            f"User request: {user_content}\n\n"
            f"Current workspace inputs:\n{workspace_context or '(no attached files)'}\n\n"
            "Return a concise answer and mention any recommended output files."
        )
        agent = DeepAgentFactory(self.settings).create(tools=[])
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": thread_id}},
        )
        content = self._extract_agent_text(result)
        return AgentResponse(content=content, plan=["deep agents 실행"], generated_files=[])

    def _extract_agent_text(self, result: object) -> str:
        if isinstance(result, dict) and "messages" in result and result["messages"]:
            last = result["messages"][-1]
            content = getattr(last, "content", None)
            if content is not None:
                return str(content)
            if isinstance(last, dict):
                return str(last.get("content", last))
        return str(result)

    def _run_fake_document_agent(
        self,
        thread_id: str,
        run_id: str,
        user_content: str,
        workspace: AgentWorkspace,
    ) -> AgentResponse:
        lower = user_content.lower()
        plan = ["첨부 문서 확인", "핵심 내용 요약", "리스크 검토", "필요한 산출물 작성"]
        input_paths = [path for path in workspace.list_paths() if path.startswith("/inputs/")]
        document_text = "\n\n".join(workspace.read(path) or "" for path in input_paths).strip()
        if not document_text:
            content = (
                "아직 첨부된 문서가 없습니다. `/attach` 또는 attachment API로 .md/.txt 파일을 추가하면 "
                "문서 요약, 리스크 분석, 고객 답변 초안을 도와드릴 수 있습니다."
            )
            return AgentResponse(content=content, plan=["일반 대화 응답"])

        summary = self._summarize(document_text)
        risks = self._risks(document_text)
        generated = []
        workspace.write("/work/notes.md", f"# Working Notes\n\n{summary}\n")
        workspace.write("/outputs/summary.md", f"# Summary\n\n{summary}\n")
        workspace.write("/outputs/risks.md", f"# Risks\n\n{risks}\n")
        generated.extend(["/work/notes.md", "/outputs/summary.md", "/outputs/risks.md"])

        if any(keyword in lower for keyword in ["검색", "research", "최근", "기준", "rag"]):
            results = self.search_provider.search(user_content)
            research = "\n".join(f"- {result.title}: {result.snippet} ({result.source})" for result in results)
            workspace.write("/research/search_results.md", f"# Search Results\n\n{research}\n")
            self.repository.save_tool_call(
                ToolCall(
                    id=new_id("tool"),
                    agent_run_id=run_id,
                    tool_name="search_reference",
                    input_summary=user_content[:200],
                    output_summary=f"{len(results)} mock results",
                    status=RunStatus.SUCCEEDED,
                )
            )
            generated.append("/research/search_results.md")

        customer_reply = self._customer_reply(summary, risks)
        if any(keyword in lower for keyword in ["고객", "답변", "reply", "발송", "send"]):
            workspace.write("/outputs/customer_reply.md", customer_reply)
            generated.append("/outputs/customer_reply.md")

        pending = None
        if any(keyword in lower for keyword in ["발송", "send"]):
            pending = ApprovalRequest(
                id=new_id("approval"),
                thread_id=thread_id,
                agent_run_id=run_id,
                requested_action="send_customer_reply",
                preview=customer_reply,
            )
            self.repository.save_approval(pending)

        content = self._compose_answer(summary, risks, generated, pending)
        return AgentResponse(content=content, generated_files=generated, pending_approval=pending, plan=plan)

    def _summarize(self, text: str) -> str:
        lines = [line.strip("#- *\t ") for line in text.splitlines() if line.strip()]
        selected = lines[:5]
        return "\n".join(f"- {line}" for line in selected) if selected else "- 요약할 텍스트가 없습니다."

    def _risks(self, text: str) -> str:
        candidates = []
        for marker in ["보관", "개인정보", "제3자", "동의", "환불", "해지", "책임", "제한"]:
            if marker in text:
                candidates.append(f"- `{marker}` 관련 조항은 근거, 범위, 고객 고지가 명확한지 확인이 필요합니다.")
        return "\n".join(candidates[:6]) if candidates else "- 명시적인 고위험 키워드는 적지만, 원문 근거 확인은 필요합니다."

    def _customer_reply(self, summary: str, risks: str) -> str:
        return (
            "# Customer Reply Draft\n\n"
            "고객님 안녕하세요. 첨부 문서를 기준으로 확인한 주요 내용은 다음과 같습니다.\n\n"
            f"## 핵심 요약\n{summary}\n\n"
            f"## 확인 필요 사항\n{risks}\n\n"
            "위 내용은 첨부 문서 기준의 검토 초안이며, 최종 안내 전 담당자 확인을 권장드립니다.\n"
        )

    def _compose_answer(
        self,
        summary: str,
        risks: str,
        generated: list[str],
        pending: ApprovalRequest | None,
    ) -> str:
        files = "\n".join(f"- {path}" for path in generated)
        approval = ""
        if pending is not None:
            approval = f"\n\n승인이 필요한 작업이 있습니다: approval_id={pending.id}, action={pending.requested_action}"
        return f"작업 계획에 따라 문서를 검토했습니다.\n\n요약:\n{summary}\n\n리스크:\n{risks}\n\n생성된 파일:\n{files}{approval}"
