"""Seed manage_legislation permission for Lex admin.

Revision ID: 004
Revises: 003
Create Date: 2026-02-08
"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

PERMISSIONS = [
    ("manage_legislation", "View Lex status, browse and search legislation"),
]


def upgrade() -> None:
    """Insert legislation admin permission. ON CONFLICT DO NOTHING for idempotency."""
    from sqlalchemy import text

    conn = op.get_bind()
    for name, description in PERMISSIONS:
        conn.execute(
            text(
                "INSERT INTO permissions (id, name, description) "
                "VALUES (gen_random_uuid(), :name, :description) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "description": description},
        )


def downgrade() -> None:
    """Remove seeded permissions."""
    from sqlalchemy import text

    conn = op.get_bind()
    names = [name for name, _ in PERMISSIONS]
    placeholders = ", ".join(f":name_{i}" for i in range(len(names)))
    params = {f"name_{i}": name for i, name in enumerate(names)}

    conn.execute(
        text(f"DELETE FROM permissions WHERE name IN ({placeholders})"),
        params,
    )
