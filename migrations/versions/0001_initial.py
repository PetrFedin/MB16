"""Initial MB16 schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("article", sa.String(length=96), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("colors", sa.JSON(), nullable=False),
        sa.Column("sizes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_products_article", "products", ["article"], unique=True)
    op.create_index("ix_products_status", "products", ["status"], unique=False)

    op.create_table(
        "product_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.create_index("ix_product_media_product_id", "product_media", ["product_id"], unique=False)

    op.create_table(
        "selection_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("selected_color", sa.String(length=64), nullable=False),
        sa.Column("selected_size", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", "selected_color", "selected_size", name="uq_selection_variant"),
    )
    op.create_index("ix_selection_items_user_id", "selection_items", ["user_id"], unique=False)
    op.create_index("ix_selection_items_product_id", "selection_items", ["product_id"], unique=False)

    op.create_table(
        "fitting_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column("requested_time", sa.Time(), nullable=False),
        sa.Column("confirmed_date", sa.Date(), nullable=True),
        sa.Column("confirmed_time", sa.Time(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("purchase_reported", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fitting_requests_user_id", "fitting_requests", ["user_id"], unique=False)
    op.create_index("ix_fitting_requests_status", "fitting_requests", ["status"], unique=False)

    op.create_table(
        "fitting_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("fitting_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_name", sa.String(length=180), nullable=False),
        sa.Column("article", sa.String(length=96), nullable=False),
        sa.Column("price_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("selected_color", sa.String(length=64), nullable=False),
        sa.Column("selected_size", sa.String(length=32), nullable=False),
        sa.Column("availability", sa.String(length=24), nullable=False),
        sa.Column("purchased_claimed", sa.Boolean(), nullable=False),
        sa.Column("sold_confirmed", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_fitting_items_request_id", "fitting_items", ["request_id"], unique=False)
    op.create_index("ix_fitting_items_product_id", "fitting_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fitting_items_product_id", table_name="fitting_items")
    op.drop_index("ix_fitting_items_request_id", table_name="fitting_items")
    op.drop_table("fitting_items")
    op.drop_index("ix_fitting_requests_status", table_name="fitting_requests")
    op.drop_index("ix_fitting_requests_user_id", table_name="fitting_requests")
    op.drop_table("fitting_requests")
    op.drop_index("ix_selection_items_product_id", table_name="selection_items")
    op.drop_index("ix_selection_items_user_id", table_name="selection_items")
    op.drop_table("selection_items")
    op.drop_index("ix_product_media_product_id", table_name="product_media")
    op.drop_table("product_media")
    op.drop_index("ix_products_status", table_name="products")
    op.drop_index("ix_products_article", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
