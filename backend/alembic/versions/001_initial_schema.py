"""Initial schema from canonical DATABASE_SCHEMA.sql.

Revision ID: 001
Revises: None
Create Date: 2026-02-06

This migration executes the canonical schema defined in
docs/architecture/DATABASE_SCHEMA.sql. That file is the single source of truth.
"""

import re
from pathlib import Path
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Path to canonical schema relative to the repo root
SCHEMA_PATH = Path(__file__).resolve().parents[3] / "docs" / "architecture" / "DATABASE_SCHEMA.sql"


def _split_sql_statements(sql: str) -> list[str]:
    """Split a SQL file into individual statements.

    Handles $$ dollar-quoted function bodies correctly.
    """
    statements: list[str] = []
    current: list[str] = []
    in_dollar_quote = False

    for line in sql.splitlines():
        stripped = line.strip()

        # Skip pure comment and blank lines between statements
        if not in_dollar_quote and not current and (stripped.startswith("--") or not stripped):
            continue

        current.append(line)

        # Track $$ dollar-quoting for function bodies
        dollar_count = line.count("$$")
        if dollar_count % 2 == 1:
            in_dollar_quote = not in_dollar_quote

        # Statement ends with ; at end of line (not inside dollar quotes)
        if not in_dollar_quote and stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            # Remove leading comment lines from statement
            stmt = re.sub(r"^(--[^\n]*\n)+", "", stmt).strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
            current = []

    return statements


def upgrade() -> None:
    schema_sql = SCHEMA_PATH.read_text()
    connection = op.get_bind()
    for stmt in _split_sql_statements(schema_sql):
        connection.execute(text(stmt))


def downgrade() -> None:
    # Drop all tables in reverse dependency order
    # Join tables first (no FKs pointing to them)
    op.execute("DROP TABLE IF EXISTS policy_definition_topic_links CASCADE")
    op.execute("DROP TABLE IF EXISTS user_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS role_permissions CASCADE")

    # Tenant-scoped tables (reverse creation order)
    op.execute("DROP TABLE IF EXISTS user_feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS semantic_cache_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_events CASCADE")
    op.execute("DROP TABLE IF EXISTS activity_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS canvases CASCADE")
    op.execute("DROP TABLE IF EXISTS news_stories CASCADE")
    op.execute("DROP TABLE IF EXISTS regulatory_change_alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS policy_reviews CASCADE")
    op.execute("DROP TABLE IF EXISTS policy_definitions CASCADE")
    op.execute("DROP TABLE IF EXISTS policy_definition_topics CASCADE")
    op.execute("DROP TABLE IF EXISTS policy_definition_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS document_annotations CASCADE")
    op.execute("DROP TABLE IF EXISTS document_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_bases CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_invocation_events CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_invocations CASCADE")
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_templates CASCADE")
    op.execute("DROP TABLE IF EXISTS guardrails CASCADE")
    op.execute("DROP TABLE IF EXISTS personas CASCADE")
    op.execute("DROP TABLE IF EXISTS roles CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    # Platform tables
    op.execute("DROP TABLE IF EXISTS permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")

    # Enum types
    op.execute("DROP TYPE IF EXISTS feedback_review_status")
    op.execute("DROP TYPE IF EXISTS feedback_rating")
    op.execute("DROP TYPE IF EXISTS activity_log_tag")
    op.execute("DROP TYPE IF EXISTS billing_feature")
    op.execute("DROP TYPE IF EXISTS billing_event_type")
    op.execute("DROP TYPE IF EXISTS alert_status")
    op.execute("DROP TYPE IF EXISTS regulatory_change_type")
    op.execute("DROP TYPE IF EXISTS rag_rating")
    op.execute("DROP TYPE IF EXISTS policy_review_state")
    op.execute("DROP TYPE IF EXISTS review_cycle")
    op.execute("DROP TYPE IF EXISTS guardrail_status")
    op.execute("DROP TYPE IF EXISTS document_processing_state")
    op.execute("DROP TYPE IF EXISTS knowledge_base_source_type")
    op.execute("DROP TYPE IF EXISTS knowledge_base_category")
    op.execute("DROP TYPE IF EXISTS model_tier")
    op.execute("DROP TYPE IF EXISTS agent_invocation_mode")
    op.execute("DROP TYPE IF EXISTS verification_status")
    op.execute("DROP TYPE IF EXISTS confidence_level")
    op.execute("DROP TYPE IF EXISTS message_state")
    op.execute("DROP TYPE IF EXISTS message_role")
    op.execute("DROP TYPE IF EXISTS conversation_state")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS subscription_tier")

    # Trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Extensions
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
