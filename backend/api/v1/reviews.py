"""回答反馈、主动转人工与人工工单管理接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import CurrentUser
from backend.db.session import get_db
from backend.models.review import TicketStatus
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.common import ApiResponse
from backend.schemas.review import (
    FeedbackCreate,
    FeedbackData,
    HandoffCreate,
    TicketData,
    TicketUpdate,
)
from backend.services.review import ReviewService

# 用户只能查看和处理自己账号下产生的反馈与工单。
router = APIRouter()


def service(session: Session) -> ReviewService:
    return ReviewService(ReviewRepository(session))


def ticket_data(item) -> TicketData:
    return TicketData.model_validate(item, from_attributes=True)


@router.post(
    "/messages/{message_id}/feedback",
    response_model=ApiResponse[FeedbackData],
    status_code=201,
)
def create_feedback(
    message_id: int,
    request: FeedbackCreate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
):
    item = service(session).create_feedback(
        message_id, user.id, request.feedback_type, request.reason
    )
    return ApiResponse(data=FeedbackData.model_validate(item, from_attributes=True))


@router.post(
    "/messages/{message_id}/handoff", response_model=ApiResponse[TicketData], status_code=201
)
def handoff(
    message_id: int,
    request: HandoffCreate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
):
    item = service(session).handoff(message_id, user.id, request.reason)
    return ApiResponse(data=ticket_data(item))


@router.get("/tickets", response_model=ApiResponse[list[TicketData]])
def list_tickets(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    status: TicketStatus | None = None,
    risk_level: Annotated[str | None, Query(max_length=20)] = None,
):
    items = service(session).list_tickets(user.id, status=status, risk_level=risk_level)
    return ApiResponse(data=[ticket_data(item) for item in items])


@router.get("/tickets/{ticket_id}", response_model=ApiResponse[TicketData])
def get_ticket(ticket_id: int, user: CurrentUser, session: Annotated[Session, Depends(get_db)]):
    return ApiResponse(data=ticket_data(service(session).get_ticket(ticket_id, user.id)))


@router.patch("/tickets/{ticket_id}", response_model=ApiResponse[TicketData])
def update_ticket(
    ticket_id: int,
    request: TicketUpdate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
):
    item = service(session).update_ticket(ticket_id, user.id, request.status, request.resolution)
    return ApiResponse(data=ticket_data(item))
