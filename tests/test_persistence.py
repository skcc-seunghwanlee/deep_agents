from sample_agents.domain.models import Message, MessageRole, new_id
from sample_agents.persistence.sqlite import SQLiteConversationRepository


def test_sqlite_repository_persists_messages(tmp_path):
    repo = SQLiteConversationRepository(f"sqlite:///{tmp_path / 'demo.db'}")
    thread = repo.create_thread("demo")
    message = Message(id=new_id("msg"), thread_id=thread.id, role=MessageRole.USER, content="hello")

    repo.save_message(message)

    assert repo.get_thread(thread.id).title == "demo"
    assert repo.list_messages(thread.id)[0].content == "hello"
