"""Add private customer product lines: Finance, Inventory, Family, Notifications.

Revision ID: 0001
Revises:
Create Date: 2026-04-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Family / Multi-Tenancy ---
    op.create_table(
        "household_workspaces",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("household_workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("role", sa.String(20), server_default="viewer"),
        sa.Column("invited_at", sa.DateTime),
        sa.Column("accepted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "routines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("household_workspaces.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("interval", sa.String(20), server_default="weekly"),
        sa.Column("assignee_strategy", sa.String(20), server_default="fixed"),
        sa.Column("current_assignee_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "routine_completions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("routine_id", sa.Integer, sa.ForeignKey("routines.id"), nullable=False),
        sa.Column("completed_by", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("photo_url", sa.String(500), nullable=True),
    )

    # --- Inventory ---
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workspace_id", sa.Integer, sa.ForeignKey("household_workspaces.id"), nullable=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("room", sa.String(100), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("value", sa.Float, nullable=True),
        sa.Column("purchase_date", sa.Date, nullable=True),
        sa.Column("receipt_doc_id", sa.Integer, sa.ForeignKey("scanned_documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "warranties",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("purchase_date", sa.Date, nullable=True),
        sa.Column("warranty_end", sa.Date, nullable=True),
        sa.Column("vendor", sa.String(200), nullable=True),
        sa.Column("receipt_doc_id", sa.Integer, sa.ForeignKey("scanned_documents.id"), nullable=True),
        sa.Column("inventory_item_id", sa.Integer, sa.ForeignKey("inventory_items.id"), nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    # --- Finance ---
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("date", sa.DateTime, nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), server_default="EUR"),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source", sa.String(10), server_default="manual"),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("monthly_limit", sa.Float, nullable=False),
        sa.Column("alert_threshold", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("interval", sa.String(20), server_default="monthly"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("cancellation_deadline", sa.Date, nullable=True),
        sa.Column("next_billing", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "finance_invoices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("recipient", sa.String(200), nullable=False),
        sa.Column("total", sa.Float, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    # --- Notifications (ersetzt alte notifications-Tabelle) ---
    op.create_table(
        "notification_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=True),
        sa.Column("user_key", sa.String(50), nullable=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("reference_id", sa.Integer, nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="new"),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("sent_at", sa.DateTime),
        sa.Column("channel", sa.String(10), server_default="inapp"),
        sa.Column("read_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("push_enabled", sa.Boolean, server_default="1"),
        sa.Column("email_enabled", sa.Boolean, server_default="1"),
        sa.Column("quiet_start", sa.String(5), server_default="22:00"),
        sa.Column("quiet_end", sa.String(5), server_default="07:00"),
        sa.UniqueConstraint("user_id", "category", name="uq_notification_pref_user_category"),
    )

    # --- ScannedDocument Erweiterung ---
    # Nur wenn die Tabelle bereits existiert (bestehende DB)
    bind = op.get_bind()
    insp = inspect(bind)
    if "scanned_documents" in insp.get_table_names():
        existing_cols = {c["name"] for c in insp.get_columns("scanned_documents")}
        new_cols = {
            "category": sa.Column("category", sa.String(50), nullable=True),
            "deadline": sa.Column("deadline", sa.Date, nullable=True),
            "ocr_confidence": sa.Column("ocr_confidence", sa.Float, nullable=True),
            "storage_location": sa.Column("storage_location", sa.String(20), nullable=True),
        }
        with op.batch_alter_table("scanned_documents") as batch_op:
            for col_name, col_def in new_cols.items():
                if col_name not in existing_cols:
                    batch_op.add_column(col_def)


def downgrade() -> None:
    # Tabellen in umgekehrter Abhaengigkeitsreihenfolge droppen
    op.drop_table("notification_preferences")
    op.drop_table("notification_events")
    op.drop_table("finance_invoices")
    op.drop_table("contracts")
    op.drop_table("budgets")
    op.drop_table("transactions")
    op.drop_table("warranties")
    op.drop_table("inventory_items")
    op.drop_table("routine_completions")
    op.drop_table("routines")
    op.drop_table("workspace_members")
    op.drop_table("household_workspaces")

    # ScannedDocument: Spalten entfernen (batch fuer SQLite)
    bind = op.get_bind()
    insp = inspect(bind)
    if "scanned_documents" in insp.get_table_names():
        existing_cols = {c["name"] for c in insp.get_columns("scanned_documents")}
        with op.batch_alter_table("scanned_documents") as batch_op:
            for col in ("storage_location", "ocr_confidence", "deadline", "category"):
                if col in existing_cols:
                    batch_op.drop_column(col)
