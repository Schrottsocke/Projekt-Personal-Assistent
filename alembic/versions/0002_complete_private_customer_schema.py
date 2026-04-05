"""Complete private customer schema: new tables, missing columns, indexes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05

Adds: invoice_items, household_documents, budget_categories tables.
Extends: contracts, finance_invoices, inventory_items, transactions with
missing columns from Issue #687.
Adds performance indexes on user_id, due_date, status.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_cols(insp, table: str) -> set[str]:
    """Return set of column names for a table, empty set if table missing."""
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _existing_indexes(insp, table: str) -> set[str]:
    """Return set of index names for a table."""
    if table not in insp.get_table_names():
        return set()
    return {idx["name"] for idx in insp.get_indexes(table) if idx["name"]}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # --- 1. New table: invoice_items ---
    if "invoice_items" not in insp.get_table_names():
        op.create_table(
            "invoice_items",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("invoice_id", sa.Integer, sa.ForeignKey("finance_invoices.id"), nullable=False),
            sa.Column("description", sa.String(300), nullable=False),
            sa.Column("quantity", sa.Float, nullable=False, server_default="1"),
            sa.Column("unit_price", sa.Float, nullable=False),
            sa.Column("total", sa.Float, nullable=False),
        )
        op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])

    # --- 2. New table: household_documents ---
    if "household_documents" not in insp.get_table_names():
        op.create_table(
            "household_documents",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("file_path", sa.String(500), nullable=True),
            sa.Column("ocr_text", sa.Text, nullable=True),
            sa.Column("deadline_date", sa.Date, nullable=True),
            sa.Column("issuer", sa.String(200), nullable=True),
            sa.Column("amount", sa.Float, nullable=True),
            sa.Column("linked_inventory_item_id", sa.Integer, sa.ForeignKey("inventory_items.id"), nullable=True),
            sa.Column("created_at", sa.DateTime),
            sa.Column("updated_at", sa.DateTime, nullable=True),
        )
        op.create_index("ix_household_documents_user_id", "household_documents", ["user_id"])

    # --- 3. New table: budget_categories ---
    if "budget_categories" not in insp.get_table_names():
        op.create_table(
            "budget_categories",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("monthly_limit", sa.Float, nullable=False),
            sa.Column("color", sa.String(20), nullable=True),
            sa.Column("icon", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime),
        )
        op.create_index("ix_budget_categories_user_id", "budget_categories", ["user_id"])

    # --- 4. Extend contracts ---
    cols = _existing_cols(insp, "contracts")
    if cols:
        new = {
            "provider": sa.Column("provider", sa.String(200), nullable=True),
            "category": sa.Column("category", sa.String(50), nullable=True),
            "end_date": sa.Column("end_date", sa.Date, nullable=True),
            "cancellation_days": sa.Column("cancellation_days", sa.Integer, nullable=True),
            "notes": sa.Column("notes", sa.Text, nullable=True),
            "updated_at": sa.Column("updated_at", sa.DateTime, nullable=True),
        }
        with op.batch_alter_table("contracts") as batch_op:
            for name, col in new.items():
                if name not in cols:
                    batch_op.add_column(col)

        indexes = _existing_indexes(insp, "contracts")
        if "ix_contracts_user_id" not in indexes:
            op.create_index("ix_contracts_user_id", "contracts", ["user_id"])
        if "ix_contracts_status" not in indexes:
            op.create_index("ix_contracts_status", "contracts", ["status"])

    # --- 5. Extend finance_invoices ---
    cols = _existing_cols(insp, "finance_invoices")
    if cols:
        new = {
            "invoice_number": sa.Column("invoice_number", sa.String(50), nullable=True),
            "recipient_address": sa.Column("recipient_address", sa.Text, nullable=True),
            "issue_date": sa.Column("issue_date", sa.Date, nullable=True),
            "tax_rate": sa.Column("tax_rate", sa.Float, nullable=True),
            "payment_date": sa.Column("payment_date", sa.Date, nullable=True),
            "notes": sa.Column("notes", sa.Text, nullable=True),
            "updated_at": sa.Column("updated_at", sa.DateTime, nullable=True),
        }
        with op.batch_alter_table("finance_invoices") as batch_op:
            for name, col in new.items():
                if name not in cols:
                    batch_op.add_column(col)

        indexes = _existing_indexes(insp, "finance_invoices")
        if "ix_finance_invoices_user_id" not in indexes:
            op.create_index("ix_finance_invoices_user_id", "finance_invoices", ["user_id"])
        if "ix_finance_invoices_due_date" not in indexes:
            op.create_index("ix_finance_invoices_due_date", "finance_invoices", ["due_date"])
        if "ix_finance_invoices_status" not in indexes:
            op.create_index("ix_finance_invoices_status", "finance_invoices", ["status"])

    # --- 6. Extend inventory_items ---
    cols = _existing_cols(insp, "inventory_items")
    if cols:
        new = {
            "box_label": sa.Column("box_label", sa.String(100), nullable=True),
            "serial_number": sa.Column("serial_number", sa.String(200), nullable=True),
            "updated_at": sa.Column("updated_at", sa.DateTime, nullable=True),
        }
        with op.batch_alter_table("inventory_items") as batch_op:
            for name, col in new.items():
                if name not in cols:
                    batch_op.add_column(col)

        indexes = _existing_indexes(insp, "inventory_items")
        if "ix_inventory_items_user_id" not in indexes:
            op.create_index("ix_inventory_items_user_id", "inventory_items", ["user_id"])

    # --- 7. Extend transactions ---
    cols = _existing_cols(insp, "transactions")
    if cols:
        if "contract_id" not in cols:
            with op.batch_alter_table("transactions") as batch_op:
                batch_op.add_column(
                    sa.Column("contract_id", sa.Integer, nullable=True)
                )
                # FK constraint added separately for SQLite compatibility

        indexes = _existing_indexes(insp, "transactions")
        if "ix_transactions_user_id" not in indexes:
            op.create_index("ix_transactions_user_id", "transactions", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # Drop indexes first
    for idx in [
        "ix_transactions_user_id",
        "ix_inventory_items_user_id",
        "ix_finance_invoices_status",
        "ix_finance_invoices_due_date",
        "ix_finance_invoices_user_id",
        "ix_contracts_status",
        "ix_contracts_user_id",
    ]:
        try:
            op.drop_index(idx)
        except Exception:
            pass

    # Remove added columns from existing tables (batch for SQLite)
    for table, columns in [
        ("transactions", ["contract_id"]),
        ("inventory_items", ["box_label", "serial_number", "updated_at"]),
        ("finance_invoices", ["invoice_number", "recipient_address", "issue_date", "tax_rate", "payment_date", "notes", "updated_at"]),
        ("contracts", ["provider", "category", "end_date", "cancellation_days", "notes", "updated_at"]),
    ]:
        if table in insp.get_table_names():
            existing = _existing_cols(insp, table)
            with op.batch_alter_table(table) as batch_op:
                for col in columns:
                    if col in existing:
                        batch_op.drop_column(col)

    # Drop new tables
    for table in ["budget_categories", "household_documents", "invoice_items"]:
        if table in insp.get_table_names():
            op.drop_table(table)
