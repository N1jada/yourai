"""Add lex_ingestion_jobs table for sidecar ingestion management.

Revision ID: 005
Revises: 004
Create Date: 2026-02-08

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create lex_ingestion_jobs table with RLS."""

    op.create_table(
        "lex_ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("mode", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_lex_ingestion_jobs_tenant_id",
        "lex_ingestion_jobs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_lex_ingestion_jobs_status",
        "lex_ingestion_jobs",
        ["status"],
    )

    # RLS — belt-and-braces with application-level filtering
    op.execute(
        """
        ALTER TABLE lex_ingestion_jobs ENABLE ROW LEVEL SECURITY;
        """
    )
    op.execute(
        """
        ALTER TABLE lex_ingestion_jobs FORCE ROW LEVEL SECURITY;
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON lex_ingestion_jobs
        USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));
        """
    )

    # updated_at trigger
    op.execute(
        """
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON lex_ingestion_jobs
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    """Drop lex_ingestion_jobs table."""
    op.drop_table("lex_ingestion_jobs")
