"""Core Atlas CRM baseline tables.

Revision ID: 20260815_00
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(), nullable=False), sa.Column("email", sa.String(), nullable=False, unique=True), sa.Column("password", sa.String(), nullable=False), sa.Column("role", sa.String()), sa.Column("is_active", sa.Boolean()), sa.Column("created_at", sa.DateTime()))
    op.create_table("projects", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String()), sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime()))
    op.create_table("project_members", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("role", sa.String()), sa.UniqueConstraint("project_id", "user_id", name="uq_project_member_user"))
    op.create_table("documents", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")), sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("original_name", sa.String()), sa.Column("file_path", sa.String()), sa.Column("file_type", sa.String()), sa.Column("created_at", sa.DateTime()), sa.Column("processing_status", sa.String()), sa.Column("processing_error", sa.Text()))
    op.create_table("modules", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")), sa.Column("name", sa.String()), sa.Column("description", sa.Text()))
    op.create_table("tasks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")), sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("title", sa.String(), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String()), sa.Column("priority", sa.String()), sa.Column("created_at", sa.DateTime()), sa.Column("module_id", sa.Integer(), sa.ForeignKey("modules.id")))
    op.create_table("checklist_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id")), sa.Column("title", sa.String(), nullable=False), sa.Column("is_completed", sa.Boolean()))
    op.create_table("activity_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("action", sa.String()), sa.Column("entity_type", sa.String()), sa.Column("entity_id", sa.Integer()), sa.Column("details", sa.Text()), sa.Column("created_at", sa.DateTime()))
    op.create_table("chat_messages", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("role", sa.String()), sa.Column("message", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade():
    for table in ("chat_messages", "activity_logs", "checklist_items", "tasks", "modules", "documents", "project_members", "projects", "users"):
        op.drop_table(table)
