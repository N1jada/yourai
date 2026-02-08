"""Add lex_legislation_index table for tracking indexed legislation in Qdrant.

Revision ID: 006
Revises: 005
Create Date: 2026-02-08

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create lex_legislation_index table with RLS."""

    op.create_table(
        "lex_legislation_index",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("legislation_id", sa.Text(), nullable=False),
        sa.Column("legislation_type", sa.String(20), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="indexed"),
        sa.Column("section_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "ingestion_job_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        sa.Column(
            "qdrant_point_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ingestion_job_id"], ["lex_ingestion_jobs.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "tenant_id", "legislation_id", name="uq_lex_legislation_index_tenant_leg"
        ),
    )
    op.create_index(
        "ix_lex_legislation_index_tenant_id",
        "lex_legislation_index",
        ["tenant_id"],
    )
    op.create_index(
        "ix_lex_legislation_index_type_year",
        "lex_legislation_index",
        ["legislation_type", "year"],
    )

    # RLS — belt-and-braces with application-level filtering
    op.execute(
        """
        ALTER TABLE lex_legislation_index ENABLE ROW LEVEL SECURITY;
        """
    )
    op.execute(
        """
        ALTER TABLE lex_legislation_index FORCE ROW LEVEL SECURITY;
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON lex_legislation_index
        USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));
        """
    )

    # updated_at trigger
    op.execute(
        """
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON lex_legislation_index
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    """Drop lex_legislation_index table."""
    op.drop_table("lex_legislation_index")
