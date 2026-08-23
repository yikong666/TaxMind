"""会话与消息数据访问。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.conversation import ChatMessage, Conversation

# owner_id 始终参与会话查询，保证聊天记录的租户隔离。


class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, conversation_id: int, owner_id: int) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.owner_id == owner_id
            )
        )

    def list(self, owner_id: int) -> list[Conversation]:
        return list(
            self.session.scalars(
                select(Conversation)
                .where(Conversation.owner_id == owner_id)
                .order_by(Conversation.updated_at.desc())
            )
        )

    def save(self, item):
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item) -> None:
        self.session.delete(item)
        self.session.commit()

    def history(self, conversation_id: int, rounds: int) -> list[ChatMessage]:
        rows = list(
            self.session.scalars(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation_id)
                .order_by(ChatMessage.id.desc())
                .limit(rounds * 2)
            )
        )
        return list(reversed(rows))
