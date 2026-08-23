"""创建回答反馈与人工工单表。 Revision ID: 20260823_06 Revises: 20260823_05"""

import sqlalchemy as sa
from alembic import op

# 外键级联保证删除用户、会话或消息后不会遗留孤立审核数据。
revision = "20260823_06"
down_revision = "20260823_05"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "message_feedbacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("feedback_type", sa.Enum("like", "dislike", name="feedbacktype"), nullable=False),
        sa.Column("reason", sa.Text()),
        *timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("owner_id", "message_id", name="uq_feedback_owner_message"),
    )
    op.create_index("ix_message_feedbacks_owner_id", "message_feedbacks", ["owner_id"])
    op.create_index("ix_message_feedbacks_message_id", "message_feedbacks", ["message_id"])
    op.create_table(
        "review_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("trigger_reason", sa.String(30), nullable=False),
        sa.Column("user_question", sa.Text(), nullable=False),
        sa.Column("ai_answer", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(20)),
        sa.Column("user_feedback", sa.Text()),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "resolved", name="ticketstatus"),
            nullable=False,
        ),
        sa.Column("resolution", sa.Text()),
        *timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("owner_id", "message_id", name="uq_ticket_owner_message"),
    )
    op.create_index("ix_review_tickets_owner_id", "review_tickets", ["owner_id"])
    op.create_index("ix_review_tickets_conversation_id", "review_tickets", ["conversation_id"])
    op.create_index("ix_review_tickets_message_id", "review_tickets", ["message_id"])


def downgrade() -> None:
    op.drop_table("review_tickets")
    op.drop_table("message_feedbacks")
