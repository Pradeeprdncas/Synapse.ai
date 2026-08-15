from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.core.database import Base


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("project_id", "identifier", name="uq_requirement_identifier"),)

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False, default="general")
    priority = Column(String, nullable=False, default="MEDIUM")
    source_section = Column(String)
    source_text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.8)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TaskProposal(Base):
    __tablename__ = "task_proposals"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    priority = Column(String, nullable=False, default="MEDIUM")
    dependencies_json = Column(Text, nullable=False, default="[]")
    acceptance_criteria_json = Column(Text, nullable=False, default="[]")
    suggested_assignee_id = Column(Integer, ForeignKey("users.id"))
    confidence = Column(Float, nullable=False, default=0.8)
    state = Column(String, nullable=False, default="PROPOSED", index=True)
    created_task_id = Column(Integer, ForeignKey("tasks.id"))
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ProposalRequirement(Base):
    __tablename__ = "proposal_requirements"
    proposal_id = Column(Integer, ForeignKey("task_proposals.id"), primary_key=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id"), primary_key=True)


class TaskRequirement(Base):
    __tablename__ = "task_requirements"
    task_id = Column(Integer, ForeignKey("tasks.id"), primary_key=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id"), primary_key=True)


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(String, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)
    input_references_json = Column(Text, nullable=False, default="[]")
    provider = Column(String, nullable=False, default="deterministic")
    model = Column(String)
    status = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=False, default=0)
    parse_success = Column(Integer, nullable=False, default=1)
    error_message = Column(Text)
    output_ids_json = Column(Text, nullable=False, default="[]")
    token_usage_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_id", name="uq_document_chunk"),)

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id"))
    chunk_id = Column(String, nullable=False)
    section = Column(String)
    source_filename = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunking_method = Column(String, nullable=False, default="structure-aware-v1")
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AssignmentRecommendation(Base):
    __tablename__ = "assignment_recommendations"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    recommended_member_id = Column(Integer, ForeignKey("project_members.id"), nullable=False)
    score = Column(Integer, nullable=False)
    score_breakdown_json = Column(Text, nullable=False)
    reasons_json = Column(Text, nullable=False)
    alternatives_json = Column(Text, nullable=False, default="[]")
    required_skills_json = Column(Text, nullable=False, default="[]")
    state = Column(String, nullable=False, default="PROPOSED")
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class GoogleConnection(Base):
    __tablename__ = "google_connections"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    email = Column(String)
    scopes_json = Column(Text, nullable=False, default="[]")
    encrypted_access_token = Column(Text)
    encrypted_refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OAuthState(Base):
    __tablename__ = "oauth_states"
    state_hash = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    task_assignment_email = Column(Integer, nullable=False, default=1)
    task_status_email = Column(Integer, nullable=False, default=0)
    daily_summary_email = Column(Integer, nullable=False, default=0)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_notification_idempotency"),)
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    kind = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING")
    provider_message_id = Column(String)
    safe_error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
