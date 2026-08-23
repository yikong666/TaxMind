"""创建知识库与文档表。

Revision ID: 20260823_02
Revises: 20260823_01
"""
import sqlalchemy as sa
from alembic import op

revision: str = "20260823_02"
down_revision: str | None = "20260823_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "kb_type",
            sa.Enum("public_policy", "local_policy", "internal", name="knowledgebasetype"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("owner_id", "name", name="uq_kb_owner_name"),
    )
    op.create_index(op.f("ix_knowledge_bases_owner_id"), "knowledge_bases", ["owner_id"])
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "parse_status",
            sa.Enum("pending", "parsing", "completed", "failed", name="parsestatus"),
            nullable=False,
        ),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("parent_chunk_count", sa.Integer(), nullable=False),
        sa.Column("child_chunk_count", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(op.f("ix_documents_knowledge_base_id"), "documents", ["knowledge_base_id"])
    op.create_index(op.f("ix_documents_parse_status"), "documents", ["parse_status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_parse_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_knowledge_base_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_knowledge_bases_owner_id"), table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
