"""回答反馈、自动转人工与工单状态流转服务。"""

import logging

from backend.core.exceptions import BusinessError
from backend.models.conversation import MessageRole, MessageStatus
from backend.models.review import MessageFeedback, ReviewTicket, TicketStatus
from backend.repositories.review_repository import ReviewRepository

logger = logging.getLogger("taxmind.review")
ALLOWED_TRANSITIONS = {
    TicketStatus.PENDING: {TicketStatus.PROCESSING},
    TicketStatus.PROCESSING: {TicketStatus.RESOLVED},
    TicketStatus.RESOLVED: set(),
}


# 工单仅针对已完成的 AI 回答创建，用户问题从同一会话的上一条消息提取。
class ReviewService:
    def __init__(self, repository: ReviewRepository):
        self.repository = repository

    def _assistant_message(self, message_id: int, owner_id: int):
        message = self.repository.get_owned_message(message_id, owner_id)
        if message is None:
            raise BusinessError("回答消息不存在", "MESSAGE_NOT_FOUND", 404)
        if message.role != MessageRole.ASSISTANT or message.status != MessageStatus.COMPLETED:
            raise BusinessError("只能反馈已完成的 AI 回答", "INVALID_FEEDBACK_MESSAGE")
        return message

    def create_feedback(self, message_id: int, owner_id: int, feedback_type, reason):
        self._assistant_message(message_id, owner_id)
        if self.repository.get_feedback(message_id, owner_id):
            raise BusinessError("该回答已经反馈过", "FEEDBACK_EXISTS", 409)
        item = self.repository.save(
            MessageFeedback(
                owner_id=owner_id,
                message_id=message_id,
                feedback_type=feedback_type,
                reason=(reason or "").strip() or None,
            )
        )
        logger.info("回答反馈已保存 message_id=%s type=%s", message_id, feedback_type)
        return item

    def handoff(self, message_id: int, owner_id: int, reason: str | None):
        message = self._assistant_message(message_id, owner_id)
        return self._create_ticket(message, owner_id, "user_handoff", reason)

    def create_auto(self, message, owner_id: int, user_question: str, trigger_reason: str):
        if self.repository.get_ticket_by_message(message.id, owner_id):
            return None
        ticket = ReviewTicket(
            owner_id=owner_id,
            conversation_id=message.conversation_id,
            message_id=message.id,
            trigger_reason=trigger_reason,
            user_question=user_question,
            ai_answer=message.content,
            citations=message.citations,
            risk_level=message.risk_level,
            status=TicketStatus.PENDING,
        )
        logger.warning("回答自动进入人工审核 message_id=%s reason=%s", message.id, trigger_reason)
        return self.repository.save(ticket)

    def _create_ticket(self, message, owner_id: int, trigger_reason: str, reason: str | None):
        if self.repository.get_ticket_by_message(message.id, owner_id):
            raise BusinessError("该回答已存在人工工单", "TICKET_EXISTS", 409)
        # 当前回答之前最近的一条消息即为本轮用户问题。
        history = self.repository.get_previous_user_message(message)
        ticket = ReviewTicket(
            owner_id=owner_id,
            conversation_id=message.conversation_id,
            message_id=message.id,
            trigger_reason=trigger_reason,
            user_question=history.content if history else "",
            ai_answer=message.content,
            citations=message.citations,
            risk_level=message.risk_level,
            user_feedback=(reason or "").strip() or None,
            status=TicketStatus.PENDING,
        )
        logger.info("人工工单已创建 message_id=%s owner_id=%s", message.id, owner_id)
        return self.repository.save(ticket)

    def list_tickets(self, owner_id: int):
        return self.repository.list_tickets(owner_id)

    def get_ticket(self, ticket_id: int, owner_id: int):
        ticket = self.repository.get_ticket(ticket_id, owner_id)
        if ticket is None:
            raise BusinessError("人工工单不存在", "TICKET_NOT_FOUND", 404)
        return ticket

    def update_ticket(self, ticket_id: int, owner_id: int, status, resolution):
        ticket = self.get_ticket(ticket_id, owner_id)
        if status not in ALLOWED_TRANSITIONS[ticket.status]:
            raise BusinessError("工单状态流转不合法", "INVALID_TICKET_TRANSITION")
        if status == TicketStatus.RESOLVED and not (resolution or "").strip():
            raise BusinessError("解决工单时必须填写处理结果", "TICKET_RESOLUTION_REQUIRED")
        ticket.status = status
        ticket.resolution = (resolution or "").strip() or None
        logger.info("人工工单状态已更新 ticket_id=%s status=%s", ticket.id, status)
        return self.repository.save(ticket)
