"""Document provider metadata for assignment context delivery.

Revision ID: 20260815_03
Revises: 20260815_02
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_03"
down_revision = "20260815_02"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("source_provider", sa.String(), nullable=True))
        batch.add_column(sa.Column("source_url", sa.String(), nullable=True))

def downgrade():
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("source_url"); batch.drop_column("source_provider")
