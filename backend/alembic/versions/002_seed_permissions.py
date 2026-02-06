"""Seed permissions from spec §2.4.

Revision ID: 002
Revises: 001
Create Date: 2026-02-06
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

# All permissions from the functional spec §2.4
PERMISSIONS = [
    # User management
    ("list_users", "List users within the tenant"),
    ("view_user", "View a specific user's profile"),
    ("create_user", "Create and invite new users"),
    ("delete_user", "Soft-delete a user"),
    ("update_user_role", "Assign or remove roles from a user"),
    ("update_user_profile", "Update a user's profile details"),
    ("update_user_preferences", "Update a user's notification preferences"),
    ("update_user_job_role", "Update a user's job role"),
    # Role management
    ("list_user_roles", "List and manage roles"),
    ("delete_user_roles", "Delete roles"),
    # Persona management
    ("list_personas", "List AI personas"),
    ("create_persona", "Create a new AI persona"),
    ("update_persona", "Update an AI persona"),
    ("delete_persona", "Delete an AI persona"),
    # Guardrail management
    ("list_guardrails", "List guardrails"),
    ("view_guardrail", "View a specific guardrail"),
    ("create_guardrail", "Create a new guardrail"),
    ("update_guardrail", "Update a guardrail"),
    ("delete_guardrail", "Delete a guardrail"),
    # Dashboard
    ("show_dashboard", "View the analytics dashboard"),
    ("show_user_management", "View the user management panel"),
    ("query_account_usage_stats", "Query account usage statistics"),
    # Activity
    ("list_activity_logs", "List activity logs"),
    ("export_activity_logs", "Export activity logs as CSV"),
    # Knowledge base
    ("create_knowledge_base", "Create a knowledge base"),
    ("delete_knowledge_base", "Delete a knowledge base"),
    ("sync_knowledge_base", "Trigger knowledge base sync"),
    ("upload_documents", "Upload documents to a knowledge base"),
    ("delete_documents", "Delete documents from a knowledge base"),
    # Compliance
    ("view_regulatory_alerts", "View regulatory change alerts"),
    ("manage_policy_review_schedule", "Manage policy definitions and review schedules"),
    ("export_compliance_reports", "Export compliance reports"),
    # Tenant admin
    ("create_tenant", "Create a new tenant"),
    ("update_tenant_settings", "Update tenant settings and configuration"),
    ("manage_tenant_billing", "Manage tenant billing and credits"),
    ("configure_industry_vertical", "Configure industry vertical settings"),
    # Operations
    ("cancel_conversation", "Cancel an in-flight conversation"),
    ("cancel_policy_review", "Cancel an in-flight policy review"),
]


def upgrade() -> None:
    """Insert all permissions. ON CONFLICT DO NOTHING for idempotency."""
    for name, description in PERMISSIONS:
        op.execute(
            f"INSERT INTO permissions (id, name, description) "
            f"VALUES (gen_random_uuid(), '{name}', '{description}') "
            f"ON CONFLICT (name) DO NOTHING"
        )


def downgrade() -> None:
    """Remove seeded permissions."""
    names = ", ".join(f"'{name}'" for name, _ in PERMISSIONS)
    op.execute(f"DELETE FROM permissions WHERE name IN ({names})")
