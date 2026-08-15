import json
import io
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.atlas_agent import AssignmentRecommendation, GoogleConnection, NotificationPreference, OAuthState, Requirement
from app.models.document import Document
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.services.assignments import classify_complexity, score_candidates
from app.services.document_chunks import structure_aware_chunks
from app.services.google_integration import consume_state
from app.services.rbac import require_permission
from app.api.routes.atlas_agent import approve_assignment
from app.schemas.atlas_agent import AssignmentApproveRequest
from app.schemas.atlas_agent import GenerateProposalRequest
from app.api.routes.atlas_agent import generate, requirements
from app.api.routes.documents import upload_document
from starlette.datastructures import UploadFile


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); session = sessionmaker(bind=engine)()
    manager = User(name="Maya", email="maya@example.test", password="x", role="MEMBER"); session.add(manager); session.flush()
    project = Project(name="Demo", owner_id=manager.id); session.add(project); session.flush()
    session.add(ProjectMember(project_id=project.id, user_id=manager.id, role="MANAGER", skills_json='["architecture"]'))
    session.commit(); yield session; session.close()


def add_member(db, project, name, role, skills, capacity=1.0):
    user = User(name=name, email=f"{name.lower()}@example.test", password="x", role="MEMBER"); db.add(user); db.flush()
    member = ProjectMember(project_id=project.id, user_id=user.id, role=role, skills_json=json.dumps(skills), current_capacity=capacity)
    db.add(member); db.flush(); return user, member


def test_structure_chunking_preserves_heading_and_metadata():
    chunks = structure_aware_chunks("# Authentication\n\n## Session Management\n\nUsers must revoke active sessions.\n\n- Tokens expire\n- Revocation is immediate")
    assert chunks and chunks[0].heading_path == "Authentication > Session Management"
    assert chunks[0].chunk_id and chunks[0].chunking_method == "structure-aware-v1"
    assert "Users must revoke" in chunks[0].text


def test_qdrant_retrieval_is_project_filtered(tmp_path, monkeypatch):
    from app.services import vector_store
    monkeypatch.setenv("ATLAS_QDRANT_PATH", str(tmp_path / "qdrant")); vector_store._client = None
    first = structure_aware_chunks("# Authentication\n\nPassword reset tokens must expire.")
    second = structure_aware_chunks("# Payments\n\nRefund webhooks must be verified.")
    vector_store.index_chunks(101, 1, "auth.md", first); vector_store.index_chunks(202, 2, "payments.md", second)
    results = vector_store.search(101, "refund webhook password", 10)
    assert results and all(item["project_id"] == 101 for item in results)
    assert all({"document_id", "chunk_id", "section", "source_filename", "chunk_index", "chunking_method", "created_at"} <= item.keys() for item in results)
    vector_store._client.close(); vector_store._client = None


def test_project_role_permissions_are_deterministic(db):
    project = db.query(Project).one()
    for role, can_approve in [("MANAGER", True), ("TEAM_LEAD", True), ("SENIOR_DEVELOPER", False), ("JUNIOR_DEVELOPER", False), ("INTERN", False)]:
        user, _ = add_member(db, project, role, role, [])
        if can_approve: require_permission(db, project.id, user, "assignments:approve")
        else:
            with pytest.raises(HTTPException) as denied: require_permission(db, project.id, user, "assignments:approve")
            assert denied.value.status_code == 403


def test_document_upload_authorizes_before_writing(db):
    project = db.query(Project).one()
    outsider = User(name="Outsider", email="outsider@example.test", password="x")
    db.add(outsider); db.commit()
    upload = UploadFile(filename="../../secret.md", file=io.BytesIO(b"Users must be authorized."))
    with pytest.raises(HTTPException) as denied:
        upload_document(project.id, upload, db, outsider)
    assert denied.value.status_code == 403


def test_junior_cannot_generate_proposals_and_only_sees_assigned_requirements(db):
    project = db.query(Project).one()
    junior, _ = add_member(db, project, "ScopedJunior", "JUNIOR_DEVELOPER", ["testing"])
    owner = db.query(User).filter_by(id=project.owner_id).one()
    document = Document(project_id=project.id, uploaded_by=owner.id, original_name="prd.md", file_path="prd.md", processing_status="READY")
    db.add(document); db.flush()
    assigned_req = Requirement(identifier="REQ-ASSIGNED", project_id=project.id, document_id=document.id, title="Assigned", description="Assigned requirement", category="general", priority="MEDIUM", source_text="Assigned requirement", confidence=.9)
    hidden_req = Requirement(identifier="REQ-HIDDEN", project_id=project.id, document_id=document.id, title="Hidden", description="Hidden requirement", category="general", priority="MEDIUM", source_text="Hidden requirement", confidence=.9)
    db.add_all([assigned_req, hidden_req]); db.flush()
    task = Task(project_id=project.id, assigned_to=junior.id, title="Assigned task"); db.add(task); db.flush()
    from app.models.atlas_agent import TaskRequirement
    db.add(TaskRequirement(task_id=task.id, requirement_id=assigned_req.id)); db.commit()
    assert [item["id"] for item in requirements(project.id, db, junior)] == ["REQ-ASSIGNED"]
    with pytest.raises(HTTPException) as denied:
        generate(project.id, GenerateProposalRequest(requirement_ids=["REQ-ASSIGNED"]), db, junior)
    assert denied.value.status_code == 403


def test_high_complexity_prefers_qualified_senior_and_excludes_intern(db):
    project = db.query(Project).one()
    _, senior = add_member(db, project, "Arun", "SENIOR_DEVELOPER", ["python", "fastapi", "authentication"])
    _, intern = add_member(db, project, "Nila", "INTERN", ["python", "authentication"])
    task = Task(project_id=project.id, title="Secure authentication API", description="Implement Python FastAPI authentication security", priority="HIGH", complexity="COMPLEX")
    db.add(task); db.flush(); candidates = score_candidates(db, task)
    assert candidates[0]["memberId"] == senior.id
    assert next(item for item in candidates if item["memberId"] == intern.id)["disqualified"] is True


def test_low_complexity_can_prefer_junior_and_overload_is_penalized(db):
    project = db.query(Project).one()
    senior_user, _ = add_member(db, project, "Senior", "SENIOR_DEVELOPER", ["documentation"])
    _, junior = add_member(db, project, "Junior", "JUNIOR_DEVELOPER", ["documentation"])
    for index in range(4): db.add(Task(project_id=project.id, assigned_to=senior_user.id, title=f"Existing {index}", priority="HIGH"))
    task = Task(project_id=project.id, title="Update documentation", description="Clean up documentation", priority="LOW", complexity="SIMPLE")
    db.add(task); db.flush(); assert score_candidates(db, task)[0]["memberId"] == junior.id


def test_complexity_classifier_is_enum_bounded():
    assert classify_complexity("HIGH", "security architecture migration", ["api"], 5) == "COMPLEX"
    assert classify_complexity("LOW", "update documentation", [], 1) == "SIMPLE"


def test_oauth_state_is_one_time_and_expiring(db):
    import hashlib
    state = "safe-state"; row = OAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(), user_id=db.query(User).first().id, expires_at=datetime.utcnow() + timedelta(minutes=1))
    db.add(row); db.commit(); assert consume_state(db, state) == row.user_id; db.commit()
    with pytest.raises(HTTPException): consume_state(db, state)
    with pytest.raises(HTTPException): consume_state(db, "wrong-state")


def test_failed_oauth_exchange_still_consumes_state(db, monkeypatch):
    from app.services import google_integration
    import hashlib
    state = "failed-exchange-state"
    db.add(OAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(), user_id=db.query(User).first().id, expires_at=datetime.utcnow() + timedelta(minutes=1)))
    db.commit()
    class FailedResponse:
        ok = False
    monkeypatch.setattr(google_integration, "config", lambda: {"client_id": "id", "client_secret": "secret", "redirect_uri": "http://callback", "success_url": "http://frontend"})
    monkeypatch.setattr(google_integration.requests, "post", lambda *a, **kw: FailedResponse())
    with pytest.raises(HTTPException):
        google_integration.exchange_code(db, state, "bad-code")
    with pytest.raises(HTTPException):
        consume_state(db, state)


def test_assignment_email_is_idempotent_and_honors_preferences(db, monkeypatch):
    from app.services import google_integration
    project = db.query(Project).one(); manager = db.query(User).filter_by(id=project.owner_id).one()
    recipient, _ = add_member(db, project, "Recipient", "JUNIOR_DEVELOPER", ["testing"])
    task = Task(project_id=project.id, title="Test task", priority="LOW"); db.add(task); db.commit()
    calls = []
    class Response:
        def raise_for_status(self): return None
        def json(self): return {"id": "gmail-message"}
    monkeypatch.setattr(google_integration, "access_token", lambda *_: "server-only-token")
    monkeypatch.setattr(google_integration.requests, "post", lambda *args, **kwargs: calls.append(kwargs) or Response())
    context = {"project": {"id": project.id, "name": project.name}, "task": {"id": task.id, "title": task.title, "priority": task.priority, "complexity": task.complexity},
        "assignee": {"id": recipient.id, "name": recipient.name, "email": recipient.email}, "requirements": [{"id": "REQ-1", "description": "Test it"}],
        "documents": [], "acceptanceCriteria": ["Tests pass"], "assignmentReason": None, "atlasTaskUrl": "http://localhost/tasks/1"}
    first = google_integration.send_assignment_email(db, manager.id, context)
    second = google_integration.send_assignment_email(db, manager.id, context)
    assert first["status"] == "SENT" and second["duplicatePrevented"] is True and len(calls) == 1
    other, _ = add_member(db, project, "Disabled", "JUNIOR_DEVELOPER", [])
    db.add(NotificationPreference(user_id=other.id, task_assignment_email=0)); db.commit()
    context["assignee"] = {"id": other.id, "name": other.name, "email": other.email}
    disabled = google_integration.send_assignment_email(db, manager.id, context)
    assert disabled["status"] == "DISABLED" and len(calls) == 1


def test_assignment_requires_approval_and_cannot_execute_twice(db):
    project = db.query(Project).one(); manager = db.query(User).filter_by(id=project.owner_id).one()
    recipient, member = add_member(db, project, "Assignee", "SENIOR_DEVELOPER", ["python"])
    task = Task(project_id=project.id, title="Python task", complexity="STANDARD"); db.add(task); db.flush()
    row = AssignmentRecommendation(project_id=project.id, task_id=task.id, recommended_member_id=member.id, score=80,
        score_breakdown_json="{}", reasons_json="[]", alternatives_json="[]", required_skills_json='["python"]')
    db.add(row); db.commit(); assert task.assigned_to is None
    result = approve_assignment(row.id, AssignmentApproveRequest(), db, manager)
    assert result["assignedUserId"] == recipient.id
    with pytest.raises(HTTPException) as duplicate: approve_assignment(row.id, AssignmentApproveRequest(), db, manager)
    assert duplicate.value.status_code == 409


def test_notification_failure_does_not_undo_assignment(db, monkeypatch):
    import importlib
    routes = importlib.import_module("app.api.routes.atlas_agent")
    project = db.query(Project).one(); manager = db.query(User).filter_by(id=project.owner_id).one()
    recipient, member = add_member(db, project, "EmailFail", "SENIOR_DEVELOPER", ["python"])
    task = Task(project_id=project.id, title="Persistent assignment", complexity="STANDARD"); db.add(task); db.flush()
    row = AssignmentRecommendation(project_id=project.id, task_id=task.id, recommended_member_id=member.id, score=80,
        score_breakdown_json="{}", reasons_json="[]", alternatives_json="[]", required_skills_json="[]")
    db.add_all([row, GoogleConnection(user_id=manager.id, scopes_json="[]")]); db.commit()
    monkeypatch.setattr(routes, "send_assignment_email", lambda *args, **kwargs: {"status": "FAILED", "safeError": "ProviderError"})
    result = routes.approve_assignment(row.id, AssignmentApproveRequest(), db, manager)
    db.refresh(task)
    assert result["notification"]["status"] == "FAILED" and task.assigned_to == recipient.id
