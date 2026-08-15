import json

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.atlas_agent import ProposalRequirement, Requirement, TaskProposal, TaskRequirement
from app.models.document import Document
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.services.atlas_agent import build_proposals, coverage, extract_requirements, parse_proposal_output, persist_proposals, persist_requirements
from app.api.routes.atlas_agent import approve, project_health, reject
from fastapi import HTTPException


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(name="Owner", email="owner@example.test", password="x", role="MANAGER")
    session.add(user); session.flush()
    project = Project(name="Demo", owner_id=user.id)
    session.add(project); session.flush()
    document = Document(project_id=project.id, uploaded_by=user.id, original_name="prd.txt", file_path="prd.txt", processing_status="READY")
    session.add(document); session.commit()
    yield session
    session.close()


def seed_requirement(db):
    project = db.query(Project).one(); document = db.query(Document).one()
    parsed = extract_requirements("Authentication:\nUsers must reset their password using their registered email.")
    return persist_requirements(db, project.id, document.id, parsed)[0]


def test_requirement_persistence_is_deduplicated(db):
    req = seed_requirement(db); db.flush()
    parsed = extract_requirements("Authentication:\nUsers must reset their password using their registered email.")
    assert persist_requirements(db, req.project_id, req.document_id, parsed) == []
    assert req.identifier.startswith("REQ-AUTH-")


def test_malformed_low_confidence_and_duplicate_outputs_are_rejected():
    with pytest.raises((ValidationError, ValueError, json.JSONDecodeError)):
        parse_proposal_output("not json")
    task = {"title": "Build login", "description": "Implement login safely", "requirement_ids": ["REQ-1"], "priority": "HIGH", "dependencies": [], "acceptance_criteria": ["Login works"], "confidence": .2}
    with pytest.raises(ValueError, match="low-confidence"):
        parse_proposal_output({"tasks": [task]})
    task["confidence"] = .9
    with pytest.raises(ValueError, match="duplicate"):
        parse_proposal_output({"tasks": [task, task]})


def test_proposals_are_not_tasks_until_approval(db):
    req = seed_requirement(db); plan = build_proposals([req])
    proposals = persist_proposals(db, req.project_id, plan, [req]); db.commit()
    assert len(proposals) == 1
    assert db.query(Task).count() == 0
    assert proposals[0].state == "PROPOSED"


def test_duplicate_task_proposals_are_prevented(db):
    req = seed_requirement(db); plan = build_proposals([req])
    assert len(persist_proposals(db, req.project_id, plan, [req])) == 1
    db.flush()
    assert persist_proposals(db, req.project_id, plan, [req]) == []


def test_coverage_partial_covered_and_traceable(db):
    req = seed_requirement(db); proposal = persist_proposals(db, req.project_id, build_proposals([req]), [req])[0]; db.flush()
    assert coverage(db, req.project_id)["partiallyCovered"] == 1
    task = Task(project_id=req.project_id, title="Approved implementation")
    db.add(task); db.flush(); db.add(TaskRequirement(task_id=task.id, requirement_id=req.id)); proposal.state = "EXECUTED"; db.flush()
    result = coverage(db, req.project_id)
    assert result["covered"] == 1 and result["coveragePercent"] == 100.0
    assert db.query(TaskRequirement).filter_by(task_id=task.id, requirement_id=req.id).one()


def test_approval_is_authorized_and_executes_once(db):
    req = seed_requirement(db); proposal = persist_proposals(db, req.project_id, build_proposals([req]), [req])[0]
    member = User(name="Member", email="member@example.test", password="x", role="MEMBER")
    db.add(member); db.flush(); db.add(ProjectMember(project_id=req.project_id, user_id=member.id, role="MEMBER")); db.commit()
    with pytest.raises(HTTPException) as denied:
        approve(proposal.id, db, member)
    assert denied.value.status_code == 403 and db.query(Task).count() == 0
    owner = db.query(User).filter_by(email="owner@example.test").one()
    result = approve(proposal.id, db, owner)
    assert result["state"] == "EXECUTED" and result["createdTaskId"]
    with pytest.raises(HTTPException) as duplicate:
        approve(proposal.id, db, owner)
    assert duplicate.value.status_code == 409 and db.query(Task).count() == 1


def test_rejection_never_creates_a_task_and_health_is_deterministic(db):
    req = seed_requirement(db); proposal = persist_proposals(db, req.project_id, build_proposals([req]), [req])[0]; db.commit()
    owner = db.query(User).filter_by(email="owner@example.test").one()
    assert reject(proposal.id, db, owner)["state"] == "REJECTED"
    assert db.query(Task).count() == 0
    health = project_health(req.project_id, db, owner)
    assert health["completionPercent"] == 0 and health["pendingApprovals"] == 0
