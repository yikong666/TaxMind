"""创建会话与聊天消息表。 Revision ID: 20260823_05 Revises: 20260823_04"""

import sqlalchemy as sa
from alembic import op

# 会话删除时级联删除消息，避免遗留无法归属的聊天记录。
revision = "20260823_05"
down_revision = "20260823_04"
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
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversations_owner_id", "conversations", ["owner_id"])
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("USER", "ASSISTANT", name="messagerole"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("GENERATING", "COMPLETED", "FAILED", name="messagestatus"),
            nullable=False,
        ),
        sa.Column("risk_level", sa.String(20)),
        sa.Column("route_source", sa.String(30)),
        sa.Column("model_name", sa.String(100)),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("history_rounds", sa.Integer()),
        *timestamps(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("conversations")
