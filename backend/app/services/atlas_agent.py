import hashlib
import json
import re
import time
import uuid
from collections import Counter

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.atlas_agent import AgentExecution, ProposalRequirement, Requirement, TaskProposal, TaskRequirement
from app.models.task import Task
from app.schemas.atlas_agent import ProposalPlan, RequirementExtraction

LOW_CONFIDENCE = 0.55
CATEGORY_WORDS = {
    "authentication": ("login", "password", "authentication", "session", "sign in"),
    "authorization": ("role", "permission", "admin", "manager"),
    "notifications": ("notify", "notification", "email", "telegram"),
    "projects": ("project", "workspace"),
    "tasks": ("task", "assignment", "assignee"),
    "api": ("api", "endpoint", "webhook", "response"),
}


def parse_requirement_output(raw: str | dict) -> RequirementExtraction:
    data = json.loads(raw) if isinstance(raw, str) else raw
    return RequirementExtraction.model_validate(data)


def parse_proposal_output(raw: str | dict) -> ProposalPlan:
    data = json.loads(raw) if isinstance(raw, str) else raw
    plan = ProposalPlan.model_validate(data)
    titles = [normalise(item.title) for item in plan.tasks]
    if any(count > 1 for count in Counter(titles).values()):
        raise ValueError("duplicate task titles in model output")
    if any(item.confidence < LOW_CONFIDENCE for item in plan.tasks):
        raise ValueError("low-confidence task proposal")
    return plan


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def category_for(text: str) -> str:
    lowered = text.lower()
    for category, words in CATEGORY_WORDS.items():
        if any(word in lowered for word in words):
            return category
    return "general"


def extract_requirements(text: str) -> RequirementExtraction:
    """Conservative, executable baseline extractor; replaceable by a schema-validating LLM adapter."""
    lines = text.splitlines()
    heading_stack = []
    section = None
    found = []
    for raw_line in lines:
        heading = re.match(r"^\s*(#{1,6})\s+(.+?)\s*$", raw_line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2).strip()
            heading_stack[:] = heading_stack[:level - 1]; heading_stack.append(title); section = " > ".join(heading_stack)
            continue
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if not line:
            continue
        if len(line) < 80 and (line.endswith(":") or line.isupper()):
            section = line.rstrip(":")
            continue
        lowered = line.lower()
        is_requirement = any(token in lowered for token in (" must ", " shall ", " should ", "users can ", "user can "))
        if not is_requirement or len(line) < 12:
            continue
        title = re.split(r"[.;]", line, maxsplit=1)[0][:100]
        found.append({
            "title": title,
            "description": line,
            "category": category_for(line),
            "priority": "HIGH" if any(x in lowered for x in ("must", "shall", "critical")) else "MEDIUM",
            "section": section,
            "source_text": line,
            "confidence": 0.84,
        })
    if not found:
        raise ValueError("No explicit requirements found; use must/shall/should language in the PRD")
    unique = {normalise(item["description"]): item for item in found}
    return RequirementExtraction.model_validate({"requirements": list(unique.values())})


def requirement_identifier(project_id: int, category: str, description: str, ordinal: int) -> str:
    digest = hashlib.sha1(f"{project_id}:{normalise(description)}".encode()).hexdigest()[:4].upper()
    return f"REQ-{category[:4].upper()}-{ordinal:03d}-{digest}"


def persist_requirements(db: Session, project_id: int, document_id: int, extraction: RequirementExtraction):
    existing = {normalise(row.description) for row in db.query(Requirement).filter_by(project_id=project_id).all()}
    created = []
    for item in extraction.requirements:
        if normalise(item.description) in existing:
            continue
        ordinal = db.query(Requirement).filter_by(project_id=project_id).count() + 1
        row = Requirement(
            identifier=requirement_identifier(project_id, item.category, item.description, ordinal),
            project_id=project_id, document_id=document_id, title=item.title,
            description=item.description, category=item.category, priority=item.priority,
            source_section=item.section, source_text=item.source_text, confidence=item.confidence,
        )
        db.add(row); db.flush(); created.append(row); existing.add(normalise(item.description))
    return created


def build_proposals(requirements: list[Requirement]) -> ProposalPlan:
    return ProposalPlan.model_validate({"tasks": [{
        "title": f"Implement: {req.title}"[:160],
        "description": f"Deliver and verify requirement {req.identifier}: {req.description}",
        "requirement_ids": [req.identifier], "priority": req.priority,
        "dependencies": [],
        "acceptance_criteria": [f"The behavior described by {req.identifier} is implemented", "Automated or documented verification passes"],
        "suggested_assignee_id": None, "confidence": 0.82,
    } for req in requirements]})


def persist_proposals(db: Session, project_id: int, plan: ProposalPlan, requirements: list[Requirement]):
    by_identifier = {r.identifier: r for r in requirements}
    existing_titles = {normalise(p.title) for p in db.query(TaskProposal).filter_by(project_id=project_id).filter(TaskProposal.state.in_(["PROPOSED", "APPROVED", "EXECUTED"])).all()}
    existing_titles |= {normalise(t.title) for t in db.query(Task).filter_by(project_id=project_id).all()}
    created = []
    for item in plan.tasks:
        if normalise(item.title) in existing_titles:
            continue
        refs = [by_identifier[value] for value in item.requirement_ids if value in by_identifier]
        if len(refs) != len(item.requirement_ids):
            raise ValueError("proposal references an unknown requirement")
        proposal = TaskProposal(project_id=project_id, title=item.title, description=item.description,
            priority=item.priority, dependencies_json=json.dumps(item.dependencies),
            acceptance_criteria_json=json.dumps(item.acceptance_criteria),
            suggested_assignee_id=item.suggested_assignee_id, confidence=item.confidence)
        db.add(proposal); db.flush()
        for req in refs: db.add(ProposalRequirement(proposal_id=proposal.id, requirement_id=req.id))
        created.append(proposal); existing_titles.add(normalise(item.title))
    return created


def record_execution(db: Session, project_id: int, action: str, started: float, status: str,
                     inputs=None, outputs=None, error=None, parse_success=True):
    row = AgentExecution(id=str(uuid.uuid4()), project_id=project_id, action_type=action,
        input_references_json=json.dumps(inputs or []), provider="deterministic", status=status,
        latency_ms=int((time.monotonic() - started) * 1000), parse_success=int(parse_success),
        error_message=str(error)[:2000] if error else None, output_ids_json=json.dumps(outputs or []))
    db.add(row)
    return row


def coverage(db: Session, project_id: int):
    requirements = db.query(Requirement).filter_by(project_id=project_id).all()
    covered_ids = {row.requirement_id for row in db.query(TaskRequirement).join(Task, Task.id == TaskRequirement.task_id).filter(Task.project_id == project_id).all()}
    partial_ids = {row.requirement_id for row in db.query(ProposalRequirement).join(TaskProposal, TaskProposal.id == ProposalRequirement.proposal_id).filter(TaskProposal.project_id == project_id, TaskProposal.state == "PROPOSED").all()} - covered_ids
    uncovered = [r for r in requirements if r.id not in covered_ids and r.id not in partial_ids]
    total = len(requirements)
    return {"requirementsTotal": total, "covered": len(covered_ids), "partiallyCovered": len(partial_ids),
            "uncovered": len(uncovered), "coveragePercent": round(len(covered_ids) / total * 100, 1) if total else 0.0,
            "uncoveredRequirements": uncovered}
