"""Seed local development users

Revision ID: 002
Revises: 001
Create Date: 2026-06-05
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


PASSWORD_HASH = "$2b$12$kJJFG/HSrWQrfY315mF8busb8rW664gOUzGK3oDQCG7OjgNCBhNrO"


def upgrade() -> None:
    op.execute(
        f"""
        INSERT INTO users (id, login, name, email, password_hash, role, status)
        VALUES
            (1, 'admin@manutech.com', 'Administrador', 'admin@manutech.com', '{PASSWORD_HASH}', 'admin', 'active'),
            (2, 'supervisor@manutech.com', 'Supervisor', 'supervisor@manutech.com', '{PASSWORD_HASH}', 'supervisor', 'active'),
            (3, 'tecnico@manutech.com', 'Tecnico', 'tecnico@manutech.com', '{PASSWORD_HASH}', 'technician', 'active'),
            (4, 'atendente@manutech.com', 'Atendente', 'atendente@manutech.com', '{PASSWORD_HASH}', 'attendant', 'active')
        ON CONFLICT (id) DO UPDATE SET
            login = EXCLUDED.login,
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            password_hash = EXCLUDED.password_hash,
            role = EXCLUDED.role,
            status = EXCLUDED.status;
        """
    )
    op.execute("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1))")


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM users
        WHERE id IN (1, 2, 3, 4)
          AND login IN (
            'admin@manutech.com',
            'supervisor@manutech.com',
            'tecnico@manutech.com',
            'atendente@manutech.com'
          );
        """
    )
    op.execute("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1))")
