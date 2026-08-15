import hashlib
import hmac
import json
import mimetypes
import os
import time
from html import escape
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.atlas_agent import AssignmentRecommendation, ProposalRequirement, Requirement, TaskProposal, TaskRequirement
from app.models.document import Document
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User


def _download_signature(document_id: int, recipient_id: int, expires: int) -> str:
    from app.core.security import SECRET_KEY
    payload = f"{document_id}:{recipient_id}:{expires}".encode()
    return hmac.new(SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()


def secure_download_url(document_id: int, recipient_id: int, ttl_seconds: int = 86400) -> str:
    expires = int(time.time()) + ttl_seconds
    signature = _download_signature(document_id, recipient_id, expires)
    base = os.getenv("ATLAS_API_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base}/documents/{document_id}/download?recipient_id={recipient_id}&expires={expires}&signature={signature}"


def validate_download(db: Session, document: Document, recipient_id: int, expires: int, signature: str):
    if expires < int(time.time()) or not hmac.compare_digest(signature, _download_signature(document.id, recipient_id, expires)):
        raise HTTPException(403, "Download link is invalid or expired")
    project = db.query(Project).filter_by(id=document.project_id).first()
    member = db.query(ProjectMember).filter_by(project_id=document.project_id, user_id=recipient_id, active=True).first()
    if not project or (project.owner_id != recipient_id and not member): raise HTTPException(403, "Recipient no longer has project access")


def build_assignment_context(db: Session, task_id: int, project_id: int, assignee_id: int):
    task = db.query(Task).filter_by(id=task_id, project_id=project_id, assigned_to=assignee_id).first()
    project = db.query(Project).filter_by(id=project_id).first()
    assignee = db.query(User).filter_by(id=assignee_id).first()
    member = db.query(ProjectMember).filter_by(project_id=project_id, user_id=assignee_id, active=True).first()
    if not task or not project or not assignee or (project.owner_id != assignee_id and not member):
        raise HTTPException(404, "Assigned task context not found")
    links = db.query(TaskRequirement).filter_by(task_id=task.id).all()
    requirement_ids = [link.requirement_id for link in links]
    requirements = db.query(Requirement).filter(Requirement.project_id == project_id, Requirement.id.in_(requirement_ids)).all() if requirement_ids else []
    if len(requirements) != len(set(requirement_ids)): raise HTTPException(409, "Task traceability contains a cross-project requirement")
    document_ids = sorted({req.document_id for req in requirements})
    documents = db.query(Document).filter(Document.project_id == project_id, Document.id.in_(document_ids)).all() if document_ids else []
    if len(documents) != len(document_ids): raise HTTPException(409, "Requirement provenance contains an invalid project document")
    proposal = db.query(TaskProposal).filter_by(project_id=project_id, created_task_id=task.id).first()
    recommendation = db.query(AssignmentRecommendation).filter_by(project_id=project_id, task_id=task.id, state="EXECUTED").order_by(AssignmentRecommendation.created_at.desc()).first()
    criteria = json.loads(proposal.acceptance_criteria_json) if proposal else []
    attachment_limit = max(0, float(os.getenv("ATLAS_EMAIL_ATTACHMENT_MAX_MB", "10"))) * 1024 * 1024
    document_data = []
    for document in documents:
        path = Path(document.file_path) if document.file_path else None
        is_google = document.source_provider == "GOOGLE_DOCS" or document.file_type == "application/vnd.google-apps.document"
        size = path.stat().st_size if path and path.is_file() else None
        attach = bool(path and path.is_file() and not is_google and size is not None and size <= attachment_limit)
        sections = sorted({req.source_section for req in requirements if req.document_id == document.id and req.source_section})
        document_data.append({"id": document.id, "filename": document.original_name, "type": document.file_type,
            "size": size, "sections": sections, "delivery": "ATTACHMENT" if attach else "LINK",
            "attachment_path": str(path) if attach else None,
            "url": document.source_url if is_google and document.source_url else secure_download_url(document.id, assignee_id)})
    frontend = os.getenv("ATLAS_FRONTEND_URL", "http://localhost:8080").rstrip("/")
    return {"project": {"id": project.id, "name": project.name},
        "task": {"id": task.id, "title": task.title, "description": task.description, "priority": task.priority, "complexity": task.complexity},
        "assignee": {"id": assignee.id, "name": assignee.name, "email": assignee.email},
        "requirements": [{"id": req.identifier, "title": req.title, "description": req.description, "section": req.source_section, "documentId": req.document_id} for req in requirements],
        "documents": document_data, "acceptanceCriteria": criteria,
        "assignmentReason": None if not recommendation else {"score": recommendation.score, "reasons": json.loads(recommendation.reasons_json)},
        "atlasTaskUrl": f"{frontend}/tasks?task={task.id}"}


def render_assignment_email(context: dict):
    task, project, assignee = context["task"], context["project"], context["assignee"]
    requirements = "\n".join(f"- {item['id']} — {item['description']}" for item in context["requirements"]) or "- No linked requirement"
    criteria = "\n".join(f"- {item}" for item in context["acceptanceCriteria"]) or "- Review the task details in Atlas"
    documents = "\n".join(f"- {item['filename']} ({item['delivery'].lower()}): {item['url']}" for item in context["documents"]) or "- No source documents"
    reason = "\n".join(f"- {item}" for item in (context["assignmentReason"] or {}).get("reasons", [])) or "- Approved by the project manager/team lead"
    plain = f"Hi {assignee['name']},\n\nYou have been assigned a new task in {project['name']}.\n\nTask: {task['title']}\nPriority: {task['priority']}\nComplexity: {task['complexity']}\n\nWhy this task exists:\n{requirements}\n\nAcceptance criteria:\n{criteria}\n\nAssignment reason:\n{reason}\n\nRelevant documents:\n{documents}\n\nOpen Atlas: {context['atlasTaskUrl']}\n"
    req_html = "".join(f"<li><strong>{escape(item['id'])}</strong> — {escape(item['description'])}</li>" for item in context["requirements"]) or "<li>No linked requirement</li>"
    criteria_html = "".join(f"<li>{escape(item)}</li>" for item in context["acceptanceCriteria"]) or "<li>Review the task details in Atlas</li>"
    docs_html = "".join(f'<li><a href="{escape(item["url"] or context["atlasTaskUrl"])}">{escape(item["filename"] or "Project document")}</a> — {escape(", ".join(item["sections"]) or "source document")}</li>' for item in context["documents"]) or "<li>No source documents</li>"
    html = f'''<html><body><p>Hi {escape(assignee['name'])},</p><p>You have been assigned a new task in <strong>{escape(project['name'])}</strong>.</p><h2>{escape(task['title'])}</h2><p><strong>Priority:</strong> {escape(task['priority'])}<br><strong>Complexity:</strong> {escape(task['complexity'])}</p><h3>Why this task exists</h3><ul>{req_html}</ul><h3>Acceptance criteria</h3><ul>{criteria_html}</ul><h3>Relevant documents</h3><ul>{docs_html}</ul><p><a href="{escape(context['atlasTaskUrl'])}">Open task in Atlas</a></p></body></html>'''
    return plain, html


def attachment_details(document: dict):
    path = document.get("attachment_path")
    if not path: return None
    mime, _ = mimetypes.guess_type(document.get("filename") or path); maintype, subtype = (mime or "application/octet-stream").split("/", 1)
    return {"path": path, "filename": document.get("filename") or Path(path).name, "maintype": maintype, "subtype": subtype}
