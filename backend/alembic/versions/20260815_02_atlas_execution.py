"""Atlas execution, team, retrieval and Google integration.

Revision ID: 20260815_02
Revises: 20260815_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_02"
down_revision = "20260815_01"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("project_members") as batch:
        batch.add_column(sa.Column("skills_json", sa.Text(), nullable=False, server_default="[]")); batch.add_column(sa.Column("experience_level", sa.String(), nullable=False, server_default="STANDARD")); batch.add_column(sa.Column("current_capacity", sa.Float(), nullable=False, server_default="1")); batch.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true())); batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("tasks") as batch: batch.add_column(sa.Column("complexity", sa.String(), nullable=False, server_default="STANDARD"))
    with op.batch_alter_table("activity_logs") as batch: batch.add_column(sa.Column("actor_type", sa.String(), nullable=False, server_default="USER"))
    op.create_table("document_chunks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False), sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id")), sa.Column("chunk_id", sa.String(), nullable=False), sa.Column("section", sa.String()), sa.Column("source_filename", sa.String(), nullable=False), sa.Column("chunk_index", sa.Integer(), nullable=False), sa.Column("chunking_method", sa.String(), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("document_id", "chunk_id", name="uq_document_chunk"))
    op.create_table("assignment_recommendations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False), sa.Column("recommended_member_id", sa.Integer(), sa.ForeignKey("project_members.id"), nullable=False), sa.Column("score", sa.Integer(), nullable=False), sa.Column("score_breakdown_json", sa.Text(), nullable=False), sa.Column("reasons_json", sa.Text(), nullable=False), sa.Column("alternatives_json", sa.Text(), nullable=False), sa.Column("required_skills_json", sa.Text(), nullable=False), sa.Column("state", sa.String(), nullable=False), sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("reviewed_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("google_connections", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True), sa.Column("email", sa.String()), sa.Column("scopes_json", sa.Text(), nullable=False), sa.Column("encrypted_access_token", sa.Text()), sa.Column("encrypted_refresh_token", sa.Text()), sa.Column("token_expires_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("oauth_states", sa.Column("state_hash", sa.String(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False), sa.Column("consumed_at", sa.DateTime()))
    op.create_table("notification_preferences", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True), sa.Column("task_assignment_email", sa.Integer(), nullable=False), sa.Column("task_status_email", sa.Integer(), nullable=False), sa.Column("daily_summary_email", sa.Integer(), nullable=False))
    op.create_table("notification_deliveries", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id")), sa.Column("kind", sa.String(), nullable=False), sa.Column("idempotency_key", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("provider_message_id", sa.String()), sa.Column("safe_error", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("idempotency_key", name="uq_notification_idempotency"))

def downgrade():
    for table in ("notification_deliveries", "notification_preferences", "oauth_states", "google_connections", "assignment_recommendations", "document_chunks"): op.drop_table(table)
    with op.batch_alter_table("activity_logs") as batch: batch.drop_column("actor_type")
    with op.batch_alter_table("tasks") as batch: batch.drop_column("complexity")
    with op.batch_alter_table("project_members") as batch:
        for column in ("created_at", "active", "current_capacity", "experience_level", "skills_json"): batch.drop_column(column)
