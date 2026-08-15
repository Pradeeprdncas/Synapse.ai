import base64
import json
from email import message_from_bytes
from email import policy

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.atlas_agent import AssignmentRecommendation, ProposalRequirement, Requirement, TaskProposal, TaskRequirement
from app.models.document import Document
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.services.assignment_context import build_assignment_context
from app.services import google_integration
from app.api.routes.atlas_agent import assignment_context


@pytest.fixture()
def context_db(tmp_path):
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); db = sessionmaker(bind=engine)()
    manager = User(name="Maya", email="maya@example.test", password="x"); assignee = User(name="Arun", email="arun@example.test", password="x")
    db.add_all([manager, assignee]); db.flush(); project = Project(name="Customer Portal", owner_id=manager.id); db.add(project); db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=assignee.id, role="SENIOR_DEVELOPER", skills_json="[]")); db.flush()
    small = tmp_path / "prd.md"; small.write_text("harmless demo PRD")
    large = tmp_path / "spec.pdf"; large.write_bytes(b"x" * 2048)
    doc1 = Document(project_id=project.id, uploaded_by=manager.id, original_name="Customer PRD.md", file_path=str(small), file_type="text/markdown", processing_status="READY")
    doc2 = Document(project_id=project.id, uploaded_by=manager.id, original_name="Authentication Spec.pdf", file_path=str(large), file_type="application/pdf", processing_status="READY")
    unrelated = Document(project_id=project.id, uploaded_by=manager.id, original_name="Unrelated.pdf", file_path=str(large), file_type="application/pdf", processing_status="READY")
    google = Document(project_id=project.id, uploaded_by=manager.id, original_name="Google Architecture", file_path=str(small), file_type="application/vnd.google-apps.document", processing_status="READY", source_provider="GOOGLE_DOCS", source_url="https://docs.google.com/document/d/demo/edit")
    db.add_all([doc1, doc2, unrelated, google]); db.flush()
    req1 = Requirement(identifier="REQ-AUTH-1", project_id=project.id, document_id=doc1.id, title="Reset", description="Users must reset passwords", category="authentication", priority="HIGH", source_section="Authentication > Reset", source_text="Users must reset passwords", confidence=.9)
    req2 = Requirement(identifier="REQ-AUTH-2", project_id=project.id, document_id=doc1.id, title="Expire", description="Tokens must expire", category="authentication", priority="HIGH", source_section="Authentication > Reset", source_text="Tokens must expire", confidence=.9)
    req3 = Requirement(identifier="REQ-ARCH-1", project_id=project.id, document_id=google.id, title="Architecture", description="Service must follow architecture", category="general", priority="MEDIUM", source_section="Architecture", source_text="Service must follow architecture", confidence=.9)
    db.add_all([req1, req2, req3]); db.flush()
    task = Task(project_id=project.id, assigned_to=assignee.id, title="Implement password reset", description="Secure reset", priority="HIGH", complexity="COMPLEX"); db.add(task); db.flush()
    proposal = TaskProposal(project_id=project.id, title=task.title, priority="HIGH", acceptance_criteria_json=json.dumps(["Token expires", "Invalid token rejected"]), dependencies_json="[]", created_task_id=task.id, state="EXECUTED"); db.add(proposal); db.flush()
    for req in (req1, req2, req3): db.add(TaskRequirement(task_id=task.id, requirement_id=req.id))
    member = db.query(ProjectMember).filter_by(user_id=assignee.id).one(); rec = AssignmentRecommendation(project_id=project.id, task_id=task.id, recommended_member_id=member.id, score=91, score_breakdown_json="{}", reasons_json='["Strong authentication match"]', alternatives_json="[]", required_skills_json='["authentication"]', state="EXECUTED"); db.add(rec); db.commit()
    yield db, manager, assignee, project, task, doc1, doc2, unrelated, google
    db.close()


def test_context_includes_requirements_deduplicates_documents_and_excludes_unrelated(context_db, monkeypatch):
    db, _, assignee, project, task, doc1, _, unrelated, google = context_db
    monkeypatch.setenv("ATLAS_EMAIL_ATTACHMENT_MAX_MB", "10")
    context = build_assignment_context(db, task.id, project.id, assignee.id)
    assert context["project"]["name"] == "Customer Portal" and context["task"]["title"] == task.title
    assert {item["id"] for item in context["requirements"]} == {"REQ-AUTH-1", "REQ-AUTH-2", "REQ-ARCH-1"}
    assert [item["id"] for item in context["documents"]].count(doc1.id) == 1
    assert unrelated.id not in {item["id"] for item in context["documents"]}
    assert next(item for item in context["documents"] if item["id"] == doc1.id)["delivery"] == "ATTACHMENT"
    google_item = next(item for item in context["documents"] if item["id"] == google.id)
    assert google_item["delivery"] == "LINK" and google_item["url"].startswith("https://docs.google.com/")


def test_oversized_document_uses_secure_link(context_db, monkeypatch):
    db, _, assignee, project, task, doc1, _, _, _ = context_db
    monkeypatch.setenv("ATLAS_EMAIL_ATTACHMENT_MAX_MB", "0.000001")
    item = next(item for item in build_assignment_context(db, task.id, project.id, assignee.id)["documents"] if item["id"] == doc1.id)
    assert item["delivery"] == "LINK" and "/documents/" in item["url"] and str(doc1.file_path) not in item["url"]


def test_gmail_receives_plain_html_and_attachment(context_db, monkeypatch):
    db, manager, assignee, project, task, *_ = context_db; context = build_assignment_context(db, task.id, project.id, assignee.id); calls = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"id": "gmail-id"}
    monkeypatch.setattr(google_integration, "access_token", lambda *_: "token")
    monkeypatch.setattr(google_integration.requests, "post", lambda *a, **kw: calls.append(kw) or Response())
    result = google_integration.send_assignment_email(db, manager.id, context)
    message = message_from_bytes(base64.urlsafe_b64decode(calls[0]["json"]["raw"]), policy=policy.default)
    payload_types = [part.get_content_type() for part in message.walk()]
    assert result["status"] == "SENT" and "text/plain" in payload_types and "text/html" in payload_types and "text/markdown" in payload_types
    rendered = message.get_body(preferencelist=("plain",)).get_content()
    assert "Customer Portal" in rendered and "REQ-AUTH-1" in rendered


def test_cross_project_traceability_is_rejected(context_db):
    db, manager, assignee, project, task, *_ = context_db
    other = Project(name="Other", owner_id=manager.id); db.add(other); db.flush()
    document = Document(project_id=other.id, uploaded_by=manager.id, original_name="secret.md", file_path="secret.md", processing_status="READY"); db.add(document); db.flush()
    requirement = Requirement(identifier="REQ-OTHER", project_id=other.id, document_id=document.id, title="Other", description="Other project secret", category="general", priority="HIGH", source_text="Other project secret", confidence=.9); db.add(requirement); db.flush(); db.add(TaskRequirement(task_id=task.id, requirement_id=requirement.id)); db.commit()
    with pytest.raises(HTTPException) as denied: build_assignment_context(db, task.id, project.id, assignee.id)
    assert denied.value.status_code == 409


def test_failed_delivery_is_recorded_and_can_retry(context_db, monkeypatch):
    db, manager, assignee, project, task, *_ = context_db; context = build_assignment_context(db, task.id, project.id, assignee.id); attempts = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"id": "retry-success"}
    monkeypatch.setattr(google_integration, "access_token", lambda *_: "token")
    def post(*args, **kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1: raise RuntimeError("provider unavailable")
        return Response()
    monkeypatch.setattr(google_integration.requests, "post", post)
    failed = google_integration.send_assignment_email(db, manager.id, context)
    retried = google_integration.send_assignment_email(db, manager.id, context)
    duplicate = google_integration.send_assignment_email(db, manager.id, context)
    assert failed["status"] == "FAILED" and retried["status"] == "SENT"
    assert duplicate["duplicatePrevented"] is True and len(attempts) == 2


def test_unauthorized_member_cannot_preview_another_assignees_context(context_db):
    db, _, _, project, task, *_ = context_db
    outsider = User(name="Nila", email="nila@example.test", password="x"); db.add(outsider); db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=outsider.id, role="INTERN", skills_json="[]")); db.commit()
    with pytest.raises(HTTPException) as denied: assignment_context(task.id, db, outsider)
    assert denied.value.status_code == 403
