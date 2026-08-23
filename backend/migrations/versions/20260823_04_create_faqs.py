"""创建 FAQ 表。

Revision ID: 20260823_04
Revises: 20260823_03
"""
import sqlalchemy as sa
from alembic import op

# FAQ 有效期和启用状态建立索引，支持在线路由快速过滤候选。

revision: str = "20260823_04"
down_revision: str | None = "20260823_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("normalized_question", sa.String(length=500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("doc_no", sa.String(length=200)),
        sa.Column("effective_start", sa.Date()),
        sa.Column("effective_end", sa.Date()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "normalized_question", name="uq_faq_owner_question"),
    )
    for column in (
        "owner_id", "region", "effective_start", "effective_end", "is_enabled",
    ):
        op.create_index(op.f(f"ix_faqs_{column}"), "faqs", [column])


def downgrade() -> None:
    for column in (
        "is_enabled", "effective_end", "effective_start", "region", "owner_id",
    ):
        op.drop_index(op.f(f"ix_faqs_{column}"), table_name="faqs")
    op.drop_table("faqs")
