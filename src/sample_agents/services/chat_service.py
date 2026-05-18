from __future__ import annotations

from sample_agents.domain.models import Message, MessageRole, new_id
from sample_agents.persistence.repositories import ConversationRepository
from sample_agents.services.agent_service import AgentService


class ChatService:
    def __init__(self, repository: ConversationRepository, agent_service: AgentService) -> None:
        self.repository = repository
        self.agent_service = agent_service

    def create_thread(self, title: str = "New conversation"):
        return self.repository.create_thread(title=title)

    def handle_message(self, thread_id: str, content: str):
        if self.repository.get_thread(thread_id) is None:
            raise ValueError(f"Thread not found: {thread_id}")
        user_message = Message(id=new_id("msg"), thread_id=thread_id, role=MessageRole.USER, content=content)
        self.repository.save_message(user_message)
        agent_response = self.agent_service.run(thread_id, user_message.id, content)
        assistant_message = Message(
            id=new_id("msg"),
            thread_id=thread_id,
            role=MessageRole.ASSISTANT,
            content=agent_response.content,
        )
        self.repository.save_message(assistant_message)
        return assistant_message, agent_response

    def list_messages(self, thread_id: str):
        if self.repository.get_thread(thread_id) is None:
            raise ValueError(f"Thread not found: {thread_id}")
        return self.repository.list_messages(thread_id)
