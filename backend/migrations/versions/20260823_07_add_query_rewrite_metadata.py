"""记录回答使用的 Query 改写策略。 Revision ID: 20260823_07 Revises: 20260823_06"""

import sqlalchemy as sa
from alembic import op

# 保存改写结果便于检索效果评估和问题追踪，不覆盖用户原始消息。
revision = "20260823_07"
down_revision = "20260823_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("retrieval_strategy", sa.String(30)))
    op.add_column("chat_messages", sa.Column("retrieval_queries", sa.JSON(), nullable=True))
    op.execute("UPDATE chat_messages SET retrieval_queries = JSON_ARRAY()")
    op.alter_column("chat_messages", "retrieval_queries", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.drop_column("chat_messages", "retrieval_queries")
    op.drop_column("chat_messages", "retrieval_strategy")
