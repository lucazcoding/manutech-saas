"""Initial schema v3 — ENUMs, tabelas, índices, triggers, RLS

Revision ID: 001
Revises:
Create Date: 2026-05-31
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUMs ────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE user_role      AS ENUM ('admin', 'supervisor', 'technician', 'attendant');
        CREATE TYPE user_status    AS ENUM ('active', 'inactive');
        CREATE TYPE order_status   AS ENUM ('open', 'in_progress', 'completed', 'cancelled');
        CREATE TYPE order_priority AS ENUM ('low', 'medium', 'high', 'urgent');
        CREATE TYPE movement_type  AS ENUM ('in', 'out');
        CREATE TYPE cost_type      AS ENUM ('material', 'labor', 'service', 'other');
        CREATE TYPE audit_action   AS ENUM ('INSERT', 'UPDATE', 'DELETE');
        CREATE TYPE budget_status  AS ENUM ('draft', 'sent', 'approved', 'rejected', 'expired');
        CREATE TYPE material_status AS ENUM ('active', 'inactive');
        CREATE TYPE asset_status   AS ENUM ('active', 'inactive');
    """)

    # ── Tabelas sem FK ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE users (
            id            BIGSERIAL    PRIMARY KEY,
            login         VARCHAR(100) NOT NULL UNIQUE,
            name          VARCHAR(150) NOT NULL,
            email         VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role          user_role    NOT NULL,
            status        user_status  NOT NULL DEFAULT 'active',
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT chk_users_email_format CHECK (email ~* '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'),
            CONSTRAINT chk_users_login_len    CHECK (char_length(login) >= 3)
        );
    """)

    op.execute("""
        CREATE TABLE assets (
            id            BIGSERIAL    PRIMARY KEY,
            name          VARCHAR(200) NOT NULL,
            model         VARCHAR(150),
            manufacturer  VARCHAR(150),
            serial_number VARCHAR(100) UNIQUE,
            location      TEXT,
            status        asset_status NOT NULL DEFAULT 'active',
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE materials (
            id                BIGSERIAL       PRIMARY KEY,
            name              VARCHAR(200)    NOT NULL,
            sku               VARCHAR(50)     NOT NULL UNIQUE,
            unit_price        NUMERIC(10,2)   NOT NULL,
            quantity_in_stock NUMERIC(10,3)   NOT NULL DEFAULT 0,
            min_quantity      NUMERIC(10,3)   NOT NULL DEFAULT 5,
            status            material_status NOT NULL DEFAULT 'active',
            created_at        TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ     NOT NULL DEFAULT now(),
            CONSTRAINT chk_materials_price   CHECK (unit_price >= 0),
            CONSTRAINT chk_materials_stock   CHECK (quantity_in_stock >= 0),
            CONSTRAINT chk_materials_min_qty CHECK (min_quantity >= 0)
        );
    """)

    # ── Tabelas com FK ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE refresh_tokens (
            id         BIGSERIAL    PRIMARY KEY,
            user_id    BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(255) NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ  NOT NULL,
            revoked    BOOLEAN      NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT chk_refresh_expiry CHECK (expires_at > created_at)
        );
    """)

    op.execute("""
        CREATE TABLE service_orders (
            id           BIGSERIAL      PRIMARY KEY,
            order_number INT            NOT NULL UNIQUE GENERATED ALWAYS AS IDENTITY,
            client_name  VARCHAR(200)   NOT NULL,
            location     TEXT           NOT NULL,
            description  TEXT,
            status       order_status   NOT NULL DEFAULT 'open',
            priority     order_priority NOT NULL DEFAULT 'medium',
            total_cost   NUMERIC(12,2)  NOT NULL DEFAULT 0.00,
            start_date   DATE,
            asset_id     BIGINT         REFERENCES assets(id) ON DELETE SET NULL,
            created_at   TIMESTAMPTZ    NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ    NOT NULL DEFAULT now(),
            CONSTRAINT chk_orders_total_cost CHECK (total_cost >= 0)
        );
    """)

    op.execute("""
        CREATE TABLE order_assignments (
            id               BIGSERIAL   PRIMARY KEY,
            service_order_id BIGINT      NOT NULL REFERENCES service_orders(id) ON DELETE CASCADE,
            technician_id    BIGINT      NOT NULL REFERENCES users(id)          ON DELETE RESTRICT,
            assigned_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            unassigned_at    TIMESTAMPTZ,
            active           BOOLEAN     NOT NULL DEFAULT TRUE,
            CONSTRAINT chk_assignment_period CHECK (unassigned_at IS NULL OR unassigned_at >= assigned_at),
            CONSTRAINT chk_assignment_active CHECK (
                (active AND unassigned_at IS NULL) OR (NOT active AND unassigned_at IS NOT NULL)
            )
        );
    """)

    op.execute("""
        CREATE TABLE stock_movements (
            id               BIGSERIAL     PRIMARY KEY,
            material_id      BIGINT        NOT NULL REFERENCES materials(id)      ON DELETE RESTRICT,
            service_order_id BIGINT                 REFERENCES service_orders(id) ON DELETE SET NULL,
            movement_type    movement_type NOT NULL,
            quantity         NUMERIC(10,3) NOT NULL,
            notes            TEXT,
            created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CONSTRAINT chk_movements_qty CHECK (quantity > 0)
        );
    """)

    op.execute("""
        CREATE TABLE service_costs (
            id               BIGSERIAL     PRIMARY KEY,
            service_order_id BIGINT        NOT NULL REFERENCES service_orders(id) ON DELETE CASCADE,
            description      VARCHAR(255)  NOT NULL,
            amount           NUMERIC(12,2) NOT NULL,
            cost_type        cost_type     NOT NULL DEFAULT 'other',
            created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CONSTRAINT chk_costs_amount CHECK (amount >= 0)
        );
    """)

    op.execute("""
        CREATE TABLE attachments (
            id               BIGSERIAL    PRIMARY KEY,
            service_order_id BIGINT       NOT NULL REFERENCES service_orders(id) ON DELETE CASCADE,
            uploaded_by      BIGINT                REFERENCES users(id)          ON DELETE SET NULL,
            file_path        VARCHAR(500) NOT NULL,
            original_name    VARCHAR(255) NOT NULL,
            mime_type        VARCHAR(100) NOT NULL,
            size_bytes       BIGINT       NOT NULL,
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT chk_attachment_size CHECK (size_bytes > 0 AND size_bytes <= 52428800),
            CONSTRAINT chk_attachment_path CHECK (file_path !~ '\\.\\.'),
            CONSTRAINT uq_attachment_path  UNIQUE (file_path)
        );
    """)

    op.execute("""
        CREATE TABLE budgets (
            id               BIGSERIAL     PRIMARY KEY,
            budget_number    INT           NOT NULL UNIQUE GENERATED ALWAYS AS IDENTITY,
            service_order_id BIGINT                 REFERENCES service_orders(id) ON DELETE SET NULL,
            client_name      VARCHAR(200)  NOT NULL,
            description      TEXT,
            total_amount     NUMERIC(12,2) NOT NULL DEFAULT 0.00,
            status           budget_status NOT NULL DEFAULT 'draft',
            valid_until      DATE,
            created_by       BIGINT                 REFERENCES users(id)          ON DELETE SET NULL,
            created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CONSTRAINT chk_budget_amount CHECK (total_amount >= 0)
        );
    """)

    op.execute("""
        CREATE TABLE budget_items (
            id          BIGSERIAL     PRIMARY KEY,
            budget_id   BIGINT        NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
            description VARCHAR(255)  NOT NULL,
            quantity    NUMERIC(10,3) NOT NULL,
            unit_price  NUMERIC(12,2) NOT NULL,
            created_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CONSTRAINT chk_bitem_qty   CHECK (quantity > 0),
            CONSTRAINT chk_bitem_price CHECK (unit_price >= 0)
        );
    """)

    op.execute("""
        CREATE TABLE audit_logs (
            id         BIGSERIAL    PRIMARY KEY,
            table_name VARCHAR(100) NOT NULL,
            record_id  BIGINT       NOT NULL,
            action     audit_action NOT NULL,
            delta      JSONB        NOT NULL,
            changed_by BIGINT                REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE notifications (
            id         BIGSERIAL    PRIMARY KEY,
            user_id    BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type       VARCHAR(100) NOT NULL,
            title      VARCHAR(200) NOT NULL,
            message    TEXT         NOT NULL,
            read       BOOLEAN      NOT NULL DEFAULT FALSE,
            related_id BIGINT,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)

    # ── Índices ───────────────────────────────────────────────────────────────
    op.execute("""
        CREATE INDEX idx_users_login_status      ON users             (login, status);
        CREATE INDEX idx_orders_status_priority  ON service_orders    (status, priority, start_date);
        CREATE INDEX idx_orders_asset            ON service_orders    (asset_id);
        CREATE INDEX idx_movements_mat_date      ON stock_movements   (material_id, created_at);
        CREATE INDEX idx_assignments_technician  ON order_assignments (technician_id);
        CREATE INDEX idx_costs_order             ON service_costs     (service_order_id);
        CREATE INDEX idx_audit_table_record      ON audit_logs        (table_name, record_id);
        CREATE INDEX idx_attachments_order       ON attachments       (service_order_id);
        CREATE INDEX idx_budgets_status          ON budgets           (status, valid_until);
        CREATE INDEX idx_budget_items_budget     ON budget_items      (budget_id);
        CREATE INDEX idx_notifications_user_read ON notifications     (user_id, read);
        CREATE INDEX idx_assets_status           ON assets            (status);

        CREATE UNIQUE INDEX uq_refresh_active    ON refresh_tokens    (user_id, token_hash) WHERE revoked = FALSE;
        CREATE UNIQUE INDEX uq_assignment_active ON order_assignments  (service_order_id, technician_id) WHERE active = TRUE;
    """)

    # ── Triggers ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_recalc_total_cost()
        RETURNS TRIGGER AS $$
        DECLARE v_order_id BIGINT;
        BEGIN
            v_order_id := COALESCE(NEW.service_order_id, OLD.service_order_id);
            UPDATE service_orders
               SET total_cost = (
                       SELECT COALESCE(SUM(amount), 0)
                         FROM service_costs
                        WHERE service_order_id = v_order_id
                   ),
                   updated_at = now()
             WHERE id = v_order_id;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_recalc_total_cost
            AFTER INSERT OR UPDATE OR DELETE ON service_costs
            FOR EACH ROW EXECUTE FUNCTION fn_recalc_total_cost();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_stock_negative_check()
        RETURNS TRIGGER AS $$
        DECLARE
            v_current     NUMERIC(10,3);
            v_new_balance NUMERIC(10,3);
        BEGIN
            SELECT quantity_in_stock INTO v_current
              FROM materials
             WHERE id = NEW.material_id
               FOR UPDATE;

            v_new_balance := CASE
                WHEN NEW.movement_type = 'out' THEN v_current - NEW.quantity
                ELSE v_current + NEW.quantity
            END;

            IF v_new_balance < 0 THEN
                RAISE EXCEPTION 'Estoque insuficiente para material %: saldo % - saída % = %',
                    NEW.material_id, v_current, NEW.quantity, v_new_balance;
            END IF;

            UPDATE materials
               SET quantity_in_stock = v_new_balance,
                   updated_at        = now()
             WHERE id = NEW.material_id;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_stock_negative_check
            BEFORE INSERT ON stock_movements
            FOR EACH ROW EXECUTE FUNCTION fn_stock_negative_check();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_audit_orders()
        RETURNS TRIGGER AS $$
        DECLARE v_delta JSONB;
        BEGIN
            SELECT jsonb_object_agg(key, jsonb_build_object('old', old_val, 'new', new_val))
              INTO v_delta
              FROM (
                SELECT key, o.value AS old_val, n.value AS new_val
                  FROM jsonb_each(to_jsonb(OLD)) o
                  JOIN jsonb_each(to_jsonb(NEW)) n USING (key)
                 WHERE o.value IS DISTINCT FROM n.value
              ) diff;

            IF v_delta IS NOT NULL THEN
                INSERT INTO audit_logs (table_name, record_id, action, delta, changed_by)
                VALUES (
                    'service_orders',
                    NEW.id,
                    'UPDATE',
                    v_delta,
                    NULLIF(current_setting('app.user_id', TRUE), '')::BIGINT
                );
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_audit_orders
            AFTER UPDATE ON service_orders
            FOR EACH ROW EXECUTE FUNCTION fn_audit_orders();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_recalc_budget_total()
        RETURNS TRIGGER AS $$
        DECLARE v_budget_id BIGINT;
        BEGIN
            v_budget_id := COALESCE(NEW.budget_id, OLD.budget_id);
            UPDATE budgets
               SET total_amount = (
                       SELECT COALESCE(SUM(quantity * unit_price), 0)
                         FROM budget_items
                        WHERE budget_id = v_budget_id
                   ),
                   updated_at   = now()
             WHERE id = v_budget_id;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_recalc_budget_total
            AFTER INSERT OR UPDATE OR DELETE ON budget_items
            FOR EACH ROW EXECUTE FUNCTION fn_recalc_budget_total();
    """)

    # ── Row Level Security ────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE users             ENABLE ROW LEVEL SECURITY;
        ALTER TABLE service_orders    ENABLE ROW LEVEL SECURITY;
        ALTER TABLE order_assignments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE service_costs     ENABLE ROW LEVEL SECURITY;
        ALTER TABLE stock_movements   ENABLE ROW LEVEL SECURITY;
        ALTER TABLE refresh_tokens    ENABLE ROW LEVEL SECURITY;
        ALTER TABLE attachments       ENABLE ROW LEVEL SECURITY;
        ALTER TABLE budgets           ENABLE ROW LEVEL SECURITY;
        ALTER TABLE notifications     ENABLE ROW LEVEL SECURITY;
        ALTER TABLE assets            ENABLE ROW LEVEL SECURITY;
    """)

    op.execute("""
        CREATE POLICY p_orders_technician_select ON service_orders
            FOR SELECT
            USING (
                current_setting('app.user_role', TRUE) IN ('admin', 'supervisor', 'attendant')
                OR id IN (
                    SELECT service_order_id FROM order_assignments
                     WHERE technician_id = NULLIF(current_setting('app.user_id', TRUE), '')::BIGINT
                )
            );

        CREATE POLICY p_refresh_owner ON refresh_tokens
            FOR ALL
            USING (user_id = NULLIF(current_setting('app.user_id', TRUE), '')::BIGINT);

        CREATE POLICY p_notifications_owner ON notifications
            FOR ALL
            USING (user_id = NULLIF(current_setting('app.user_id', TRUE), '')::BIGINT);

        CREATE POLICY p_assets_all_read ON assets
            FOR SELECT
            USING (TRUE);
    """)


def downgrade() -> None:
    op.execute("""
        DROP POLICY IF EXISTS p_assets_all_read        ON assets;
        DROP POLICY IF EXISTS p_notifications_owner    ON notifications;
        DROP POLICY IF EXISTS p_refresh_owner          ON refresh_tokens;
        DROP POLICY IF EXISTS p_orders_technician_select ON service_orders;

        DROP TRIGGER IF EXISTS trg_recalc_budget_total ON budget_items;
        DROP TRIGGER IF EXISTS trg_audit_orders        ON service_orders;
        DROP TRIGGER IF EXISTS trg_stock_negative_check ON stock_movements;
        DROP TRIGGER IF EXISTS trg_recalc_total_cost   ON service_costs;

        DROP FUNCTION IF EXISTS fn_recalc_budget_total();
        DROP FUNCTION IF EXISTS fn_audit_orders();
        DROP FUNCTION IF EXISTS fn_stock_negative_check();
        DROP FUNCTION IF EXISTS fn_recalc_total_cost();

        DROP TABLE IF EXISTS notifications;
        DROP TABLE IF EXISTS audit_logs;
        DROP TABLE IF EXISTS budget_items;
        DROP TABLE IF EXISTS budgets;
        DROP TABLE IF EXISTS attachments;
        DROP TABLE IF EXISTS service_costs;
        DROP TABLE IF EXISTS stock_movements;
        DROP TABLE IF EXISTS order_assignments;
        DROP TABLE IF EXISTS service_orders;
        DROP TABLE IF EXISTS refresh_tokens;
        DROP TABLE IF EXISTS materials;
        DROP TABLE IF EXISTS assets;
        DROP TABLE IF EXISTS users;

        DROP TYPE IF EXISTS asset_status;
        DROP TYPE IF EXISTS material_status;
        DROP TYPE IF EXISTS budget_status;
        DROP TYPE IF EXISTS audit_action;
        DROP TYPE IF EXISTS cost_type;
        DROP TYPE IF EXISTS movement_type;
        DROP TYPE IF EXISTS order_priority;
        DROP TYPE IF EXISTS order_status;
        DROP TYPE IF EXISTS user_status;
        DROP TYPE IF EXISTS user_role;
    """)
