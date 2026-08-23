"""创建政策元数据与 Parent-Child Chunk 表。

Revision ID: 20260823_03
Revises: 20260823_02
"""
import sqlalchemy as sa
from alembic import op

revision: str = "20260823_03"
down_revision: str | None = "20260823_02"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
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
        "policy_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("policy_title", sa.String(length=500)),
        sa.Column("doc_no", sa.String(length=200)),
        sa.Column("region", sa.String(length=100)),
        sa.Column("tax_type", sa.String(length=100)),
        sa.Column("taxpayer_type", sa.String(length=100)),
        sa.Column("publish_date", sa.Date()),
        sa.Column("effective_start", sa.Date()),
        sa.Column("effective_end", sa.Date()),
        sa.Column(
            "policy_status",
            sa.Enum("active", "expired", "replaced", name="policystatus"),
        ),
        sa.Column("source_url", sa.Text()),
        *timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    for column in (
        "document_id", "doc_no", "region", "tax_type", "taxpayer_type",
        "effective_start", "effective_end", "policy_status",
    ):
        op.create_index(op.f(f"ix_policy_metadata_{column}"), "policy_metadata", [column])

    op.create_table(
        "parent_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=500)),
        sa.Column("content", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_parent_document_index"),
    )
    op.create_index(op.f("ix_parent_chunks_document_id"), "parent_chunks", ["document_id"])

    op.create_table(
        "child_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "vector_status",
            sa.Enum("pending", "indexed", "failed", name="vectorstatus"),
            nullable=False,
        ),
        sa.Column("vector_id", sa.String(length=100)),
        *timestamps(),
        sa.ForeignKeyConstraint(["parent_id"], ["parent_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "chunk_index", name="uq_child_parent_index"),
        sa.UniqueConstraint("vector_id"),
    )
    op.create_index(op.f("ix_child_chunks_parent_id"), "child_chunks", ["parent_id"])
    op.create_index(op.f("ix_child_chunks_vector_status"), "child_chunks", ["vector_status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_child_chunks_vector_status"), table_name="child_chunks")
    op.drop_index(op.f("ix_child_chunks_parent_id"), table_name="child_chunks")
    op.drop_table("child_chunks")
    op.drop_index(op.f("ix_parent_chunks_document_id"), table_name="parent_chunks")
    op.drop_table("parent_chunks")
    for column in (
        "policy_status", "effective_end", "effective_start", "taxpayer_type",
        "tax_type", "region", "doc_no", "document_id",
    ):
        op.drop_index(op.f(f"ix_policy_metadata_{column}"), table_name="policy_metadata")
    op.drop_table("policy_metadata")
