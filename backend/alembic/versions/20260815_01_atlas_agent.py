"""Add Atlas Agent requirements, proposals, traceability, and execution logs.

Revision ID: 20260815_01
Revises:
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_01"
down_revision = "20260815_00"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("requirements", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("identifier", sa.String(), nullable=False), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False), sa.Column("title", sa.String(), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("category", sa.String(), nullable=False), sa.Column("priority", sa.String(), nullable=False), sa.Column("source_section", sa.String()), sa.Column("source_text", sa.Text(), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("project_id", "identifier", name="uq_requirement_identifier"))
    op.create_table("task_proposals", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("title", sa.String(), nullable=False), sa.Column("description", sa.Text()), sa.Column("priority", sa.String(), nullable=False), sa.Column("dependencies_json", sa.Text(), nullable=False), sa.Column("acceptance_criteria_json", sa.Text(), nullable=False), sa.Column("suggested_assignee_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("state", sa.String(), nullable=False), sa.Column("created_task_id", sa.Integer(), sa.ForeignKey("tasks.id")), sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("reviewed_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("proposal_requirements", sa.Column("proposal_id", sa.Integer(), sa.ForeignKey("task_proposals.id"), primary_key=True), sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id"), primary_key=True))
    op.create_table("task_requirements", sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), primary_key=True), sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id"), primary_key=True))
    op.create_table("agent_executions", sa.Column("id", sa.String(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("action_type", sa.String(), nullable=False), sa.Column("input_references_json", sa.Text(), nullable=False), sa.Column("provider", sa.String(), nullable=False), sa.Column("model", sa.String()), sa.Column("status", sa.String(), nullable=False), sa.Column("latency_ms", sa.Integer(), nullable=False), sa.Column("parse_success", sa.Integer(), nullable=False), sa.Column("error_message", sa.Text()), sa.Column("output_ids_json", sa.Text(), nullable=False), sa.Column("token_usage_json", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade():
    for table in ("agent_executions", "task_requirements", "proposal_requirements", "task_proposals", "requirements"):
        op.drop_table(table)
