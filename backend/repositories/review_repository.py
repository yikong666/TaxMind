"""回答反馈与人工工单数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.conversation import ChatMessage, Conversation, MessageRole
from backend.models.review import MessageFeedback, ReviewTicket, TicketStatus


# 所有消息查询均联结会话 owner_id，防止跨用户反馈或转人工。
class ReviewRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_owned_message(self, message_id: int, owner_id: int) -> ChatMessage | None:
        return self.session.scalar(
            select(ChatMessage)
            .join(Conversation, Conversation.id == ChatMessage.conversation_id)
            .where(ChatMessage.id == message_id, Conversation.owner_id == owner_id)
        )

    def get_feedback(self, message_id: int, owner_id: int) -> MessageFeedback | None:
        return self.session.scalar(
            select(MessageFeedback).where(
                MessageFeedback.message_id == message_id,
                MessageFeedback.owner_id == owner_id,
            )
        )

    def get_ticket_by_message(self, message_id: int, owner_id: int) -> ReviewTicket | None:
        return self.session.scalar(
            select(ReviewTicket).where(
                ReviewTicket.message_id == message_id,
                ReviewTicket.owner_id == owner_id,
            )
        )

    def get_previous_user_message(self, message: ChatMessage) -> ChatMessage | None:
        return self.session.scalar(
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == message.conversation_id,
                ChatMessage.id < message.id,
                ChatMessage.role == MessageRole.USER,
            )
            .order_by(ChatMessage.id.desc())
            .limit(1)
        )

    def get_ticket(self, ticket_id: int, owner_id: int) -> ReviewTicket | None:
        return self.session.scalar(
            select(ReviewTicket).where(
                ReviewTicket.id == ticket_id, ReviewTicket.owner_id == owner_id
            )
        )

    def list_tickets(
        self,
        owner_id: int,
        status: TicketStatus | None = None,
        risk_level: str | None = None,
    ) -> list[ReviewTicket]:
        statement = select(ReviewTicket).where(ReviewTicket.owner_id == owner_id)
        if status is not None:
            statement = statement.where(ReviewTicket.status == status)
        if risk_level:
            statement = statement.where(ReviewTicket.risk_level == risk_level)
        return list(self.session.scalars(statement.order_by(ReviewTicket.created_at.desc())))

    def save(self, item):
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item
