"""Add policy tables for WP6.

Revision ID: 003
Revises: 002
Create Date: 2026-02-07

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create policy-related tables."""
    
    # Create policy_definition_groups table
    op.create_table(
        "policy_definition_groups",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_policy_definition_groups_tenant_id",
        "policy_definition_groups",
        ["tenant_id"],
    )
    
    # Create policy_definition_topics table
    op.create_table(
        "policy_definition_topics",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_policy_definition_topics_tenant_id",
        "policy_definition_topics",
        ["tenant_id"],
    )
    
    # Create policy_definitions table
    op.create_table(
        "policy_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("group_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("review_cycle", sa.Text(), nullable=True),
        sa.Column("name_variants", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("scoring_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("compliance_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("required_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("legislation_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("last_regulatory_update_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("regulatory_change_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["policy_definition_groups.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "uri", name="uq_policy_definitions_tenant_uri"),
    )
    op.create_index(
        "ix_policy_definitions_tenant_id",
        "policy_definitions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_policy_definitions_group_id",
        "policy_definitions",
        ["group_id"],
    )
    op.create_index(
        "ix_policy_definitions_status",
        "policy_definitions",
        ["status"],
    )
    
    # Create policy_definition_topics_map join table
    op.create_table(
        "policy_definition_topics_map",
        sa.Column("policy_definition_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_definition_id"],
            ["policy_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["policy_definition_topics.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("policy_definition_id", "topic_id"),
    )
    
    # Create policy_reviews table
    op.create_table(
        "policy_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("policy_definition_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("state", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("citation_verification_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_definition_id"], ["policy_definitions.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_policy_reviews_tenant_id",
        "policy_reviews",
        ["tenant_id"],
    )
    op.create_index(
        "ix_policy_reviews_user_id",
        "policy_reviews",
        ["user_id"],
    )
    op.create_index(
        "ix_policy_reviews_policy_definition_id",
        "policy_reviews",
        ["policy_definition_id"],
    )
    op.create_index(
        "ix_policy_reviews_state",
        "policy_reviews",
        ["state"],
    )
    
    # Create RLS policies (belt-and-braces with application-level filtering)
    # Note: RLS enabled via SQL in DATABASE_SCHEMA.sql setup
    op.execute(
        """
        CREATE POLICY tenant_isolation ON policy_definition_groups
        USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON policy_definition_topics
        USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON policy_definitions
        USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON policy_reviews
        USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));
        """
    )
    
    # Create updated_at triggers
    op.execute(
        """
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON policy_definition_groups
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
    op.execute(
        """
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON policy_definition_topics
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
    op.execute(
        """
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON policy_definitions
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
    op.execute(
        """
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON policy_reviews
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    """Drop policy-related tables."""
    op.drop_table("policy_reviews")
    op.drop_table("policy_definition_topics_map")
    op.drop_table("policy_definitions")
    op.drop_table("policy_definition_topics")
    op.drop_table("policy_definition_groups")
