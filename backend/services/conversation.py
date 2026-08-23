"""会话管理与消息持久化服务。"""

from backend.core.exceptions import BusinessError
from backend.models.conversation import ChatMessage, Conversation, MessageRole, MessageStatus
from backend.repositories.conversation_repository import ConversationRepository


# 生成中消息先落库，流式失败时仍能保留诊断状态。
class ConversationService:
    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    def get(self, conversation_id, owner_id):
        item = self.repository.get(conversation_id, owner_id)
        if item is None:
            raise BusinessError("会话不存在", "CONVERSATION_NOT_FOUND", 404)
        return item

    def create(self, owner_id, title):
        return self.repository.save(Conversation(owner_id=owner_id, title=title.strip()))

    def list(self, owner_id):
        return self.repository.list(owner_id)

    def rename(self, conversation_id, owner_id, title):
        item = self.get(conversation_id, owner_id)
        item.title = title.strip()
        return self.repository.save(item)

    def delete(self, conversation_id, owner_id):
        self.repository.delete(self.get(conversation_id, owner_id))

    def add_user(self, conversation_id, content):
        return self.repository.save(
            ChatMessage(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=content,
                status=MessageStatus.COMPLETED,
                citations=[],
            )
        )

    def add_assistant(self, conversation_id, model, rounds):
        return self.repository.save(
            ChatMessage(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="",
                status=MessageStatus.GENERATING,
                model_name=model,
                history_rounds=rounds,
                citations=[],
            )
        )
