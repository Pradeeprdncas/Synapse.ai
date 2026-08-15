import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.atlas_agent import AssignmentRecommendation, GoogleConnection, ProposalRequirement, Requirement, TaskProposal, TaskRequirement
from app.models.activity_log import ActivityLog
from app.models.document import Document
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.atlas_agent import AssignmentApproveRequest, GenerateProposalRequest, ProjectMemberCreate, ProposalUpdate, RetrievalRequest
from app.services.vector_store import search as vector_search
from app.services.assignments import classify_complexity, required_skills, score_candidates, workload
from app.services.activity_logger import log_activity
from app.services.rbac import require_permission
from app.services.google_integration import send_assignment_email
from app.services.assignment_context import build_assignment_context
from app.services.atlas_agent import build_proposals, coverage, extract_requirements, persist_proposals, persist_requirements, record_execution
from app.services.documents.extractor import extract_text

router = APIRouter(tags=["Atlas Agent"])


def require_project_access(db: Session, project_id: int, user: User):
    return require_permission(db, project_id, user, "project:view")[0]


def require_approver(db: Session, project_id: int, user: User):
    require_permission(db, project_id, user, "proposal:review")


def requirement_json(row: Requirement, db: Session):
    links = db.query(TaskRequirement).filter_by(requirement_id=row.id).all()
    proposals = db.query(ProposalRequirement).filter_by(requirement_id=row.id).all()
    return {"id": row.identifier, "databaseId": row.id, "projectId": row.project_id,
        "title": row.title, "description": row.description, "category": row.category,
        "priority": row.priority, "confidence": row.confidence,
        "source": {"documentId": row.document_id, "section": row.source_section, "text": row.source_text},
        "taskIds": [link.task_id for link in links], "proposalIds": [link.proposal_id for link in proposals]}


def proposal_json(row: TaskProposal, db: Session):
    links = db.query(ProposalRequirement).filter_by(proposal_id=row.id).all()
    reqs = db.query(Requirement).filter(Requirement.id.in_([x.requirement_id for x in links])).all() if links else []
    return {"id": row.id, "projectId": row.project_id, "title": row.title, "description": row.description,
        "priority": row.priority, "dependencies": json.loads(row.dependencies_json),
        "acceptanceCriteria": json.loads(row.acceptance_criteria_json), "suggestedAssigneeId": row.suggested_assignee_id,
        "confidence": row.confidence, "state": row.state, "createdTaskId": row.created_task_id,
        "requirementIds": [r.identifier for r in reqs], "createdAt": row.created_at}


@router.post("/projects/{project_id}/agent/analyze")
def analyze(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "agent:run")
    documents = db.query(Document).filter_by(project_id=project_id, processing_status="READY").order_by(Document.created_at).all()
    if not documents:
        raise HTTPException(400, "Upload and process a project document first")
    started = time.monotonic()
    created_requirements, created_proposals = [], []
    try:
        for document in documents:
            extraction = extract_requirements(extract_text(document.file_path))
            created_requirements.extend(persist_requirements(db, project_id, document.id, extraction))
        db.flush()
        targets = created_requirements or db.query(Requirement).filter_by(project_id=project_id).all()
        created_proposals = persist_proposals(db, project_id, build_proposals(targets), targets)
        execution = record_execution(db, project_id, "REQUIREMENT_EXTRACTION", started, "SUCCEEDED",
            [d.id for d in documents], [r.identifier for r in created_requirements] + [p.id for p in created_proposals])
        log_activity(db, project_id, current_user.id, "PRD_ANALYZED", "PROJECT", project_id,
            {"requirementsCreated": len(created_requirements), "proposalsCreated": len(created_proposals)}, actor_type="AGENT")
        db.commit()
        return {"executionId": execution.id, "requirementsCreated": len(created_requirements), "proposalsCreated": len(created_proposals)}
    except Exception as exc:
        db.rollback(); record_execution(db, project_id, "REQUIREMENT_EXTRACTION", started, "FAILED", [d.id for d in documents], error=exc, parse_success=False); db.commit()
        raise HTTPException(422, f"Atlas analysis failed safely: {exc}")


@router.get("/projects/{project_id}/requirements")
def requirements(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _, _, role = require_permission(db, project_id, current_user, "project:view")
    query = db.query(Requirement).filter_by(project_id=project_id)
    if role.value in ("JUNIOR_DEVELOPER", "INTERN"):
        query = query.join(TaskRequirement, TaskRequirement.requirement_id == Requirement.id).join(Task, Task.id == TaskRequirement.task_id).filter(Task.assigned_to == current_user.id)
    return [requirement_json(row, db) for row in query.distinct().order_by(Requirement.id).all()]


@router.post("/projects/{project_id}/retrieval/search")
def retrieval_search(project_id: int, request: RetrievalRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _, _, role = require_permission(db, project_id, current_user, "project:view")
    if role.value in ("JUNIOR_DEVELOPER", "INTERN"):
        raise HTTPException(403, "This project role cannot search the full project corpus")
    return {"query": request.query, "results": vector_search(project_id, request.query, request.top_k)}


@router.get("/projects/{project_id}/coverage")
def project_coverage(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_project_access(db, project_id, current_user); result = coverage(db, project_id)
    return {key: value for key, value in result.items() if key != "uncoveredRequirements"}


@router.get("/projects/{project_id}/health")
def project_health(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "analytics:view"); tasks = db.query(Task).filter_by(project_id=project_id).all(); result = coverage(db, project_id)
    done = sum(task.status.upper() in ("DONE", "COMPLETED") for task in tasks)
    return {"completionPercent": round(done / len(tasks) * 100, 1) if tasks else 0.0,
        "requirementCoveragePercent": result["coveragePercent"], "prdCoveragePercent": result["coveragePercent"], "blockedTasks": sum(t.status.upper() == "BLOCKED" for t in tasks),
        "unassignedTasks": sum(t.assigned_to is None for t in tasks), "overdueTasks": None, "overdueTrackingSupported": False,
        "uncoveredRequirements": result["uncovered"],
        "pendingTaskApprovals": db.query(TaskProposal).filter_by(project_id=project_id, state="PROPOSED").count(),
        "pendingApprovals": db.query(TaskProposal).filter_by(project_id=project_id, state="PROPOSED").count(),
        "pendingAssignmentApprovals": db.query(AssignmentRecommendation).filter_by(project_id=project_id, state="PROPOSED").count(),
        "members": db.query(ProjectMember).filter_by(project_id=project_id, active=True).count(),
        "membersWithHighWorkload": sum(workload(db, m)["workloadIndicator"] == "HIGH" for m in db.query(ProjectMember).filter_by(project_id=project_id, active=True).all())}


@router.get("/projects/{project_id}/task-proposals")
def proposals(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _, _, role = require_permission(db, project_id, current_user, "project:view")
    if role.value in ("JUNIOR_DEVELOPER", "INTERN"):
        raise HTTPException(403, "This project role cannot view task proposals")
    return [proposal_json(row, db) for row in db.query(TaskProposal).filter_by(project_id=project_id).order_by(TaskProposal.created_at.desc()).all()]


@router.post("/projects/{project_id}/task-proposals/generate")
def generate(project_id: int, request: GenerateProposalRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "agent:run")
    reqs = db.query(Requirement).filter(Requirement.project_id == project_id, Requirement.identifier.in_(request.requirement_ids)).all()
    if len(reqs) != len(set(request.requirement_ids)): raise HTTPException(400, "One or more requirement IDs are invalid")
    created = persist_proposals(db, project_id, build_proposals(reqs), reqs); db.commit()
    return [proposal_json(row, db) for row in created]


@router.patch("/task-proposals/{proposal_id}")
def update_proposal(proposal_id: int, update: ProposalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(TaskProposal).filter_by(id=proposal_id).first()
    if not row: raise HTTPException(404, "Proposal not found")
    require_approver(db, row.project_id, current_user)
    if row.state != "PROPOSED": raise HTTPException(409, "Only proposed work can be edited")
    values = update.model_dump(exclude_unset=True)
    for key in ("title", "description", "priority", "suggested_assignee_id"):
        if key in values: setattr(row, key, values[key])
    if "dependencies" in values: row.dependencies_json = json.dumps(values["dependencies"])
    if "acceptance_criteria" in values: row.acceptance_criteria_json = json.dumps(values["acceptance_criteria"])
    db.commit(); db.refresh(row); return proposal_json(row, db)


@router.post("/task-proposals/{proposal_id}/approve")
def approve(proposal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(TaskProposal).filter_by(id=proposal_id).first()
    if not row: raise HTTPException(404, "Proposal not found")
    require_approver(db, row.project_id, current_user)
    if row.state != "PROPOSED": raise HTTPException(409, "Proposal is no longer awaiting approval")
    row.state = "APPROVED"; db.flush()
    task = Task(project_id=row.project_id, title=row.title, description=row.description, priority=row.priority,
        assigned_to=None, complexity=classify_complexity(row.priority, row.description or "", json.loads(row.dependencies_json), len(json.loads(row.acceptance_criteria_json))))
    db.add(task); db.flush()
    links = db.query(ProposalRequirement).filter_by(proposal_id=row.id).all()
    for link in links: db.add(TaskRequirement(task_id=task.id, requirement_id=link.requirement_id))
    row.created_task_id = task.id; row.reviewed_by = current_user.id; row.reviewed_at = datetime.utcnow(); row.state = "EXECUTED"
    log_activity(db, row.project_id, current_user.id, "TASK_PROPOSAL_APPROVED", "TASK", task.id, {"proposalId": row.id, "complexity": task.complexity})
    db.commit(); return proposal_json(row, db)


@router.post("/task-proposals/{proposal_id}/reject")
def reject(proposal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(TaskProposal).filter_by(id=proposal_id).first()
    if not row: raise HTTPException(404, "Proposal not found")
    require_approver(db, row.project_id, current_user)
    if row.state != "PROPOSED": raise HTTPException(409, "Proposal is no longer awaiting approval")
    row.state = "REJECTED"; row.reviewed_by = current_user.id; row.reviewed_at = datetime.utcnow(); db.commit()
    return proposal_json(row, db)


@router.get("/tasks/{task_id}/traceability")
def traceability(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter_by(id=task_id).first()
    if not task: raise HTTPException(404, "Task not found")
    _, _, role = require_permission(db, task.project_id, current_user, "project:view")
    if role.value in ("JUNIOR_DEVELOPER", "INTERN") and task.assigned_to != current_user.id:
        raise HTTPException(403, "Only assigned task context is visible")
    links = db.query(TaskRequirement).filter_by(task_id=task.id).all()
    reqs = db.query(Requirement).filter(Requirement.id.in_([x.requirement_id for x in links])).all() if links else []
    return {"task": {"id": task.id, "title": task.title}, "why": [requirement_json(req, db) for req in reqs]}


def recommendation_json(row: AssignmentRecommendation):
    return {"id": row.id, "projectId": row.project_id, "taskId": row.task_id,
        "recommendedMemberId": row.recommended_member_id, "score": row.score,
        "breakdown": json.loads(row.score_breakdown_json), "reason": json.loads(row.reasons_json),
        "alternatives": json.loads(row.alternatives_json), "requiredSkills": json.loads(row.required_skills_json),
        "state": row.state, "requiresApproval": True}


@router.post("/projects/{project_id}/members")
def add_member(project_id: int, request: ProjectMemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "members:manage")
    if not db.query(User).filter_by(id=request.user_id).first(): raise HTTPException(404, "User not found")
    if db.query(ProjectMember).filter_by(project_id=project_id, user_id=request.user_id).first(): raise HTTPException(409, "User is already a project member")
    member = ProjectMember(project_id=project_id, user_id=request.user_id, role=request.project_role,
        skills_json=json.dumps(sorted({skill.strip().lower() for skill in request.skills if skill.strip()})),
        experience_level=request.experience_level, current_capacity=request.current_capacity)
    db.add(member); db.flush(); log_activity(db, project_id, current_user.id, "PROJECT_MEMBER_ADDED", "PROJECT_MEMBER", member.id, {"projectRole": member.role}); db.commit()
    return workload(db, member)


@router.get("/projects/{project_id}/members")
def project_members(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "analytics:view")
    return [workload(db, member) for member in db.query(ProjectMember).filter_by(project_id=project_id, active=True).order_by(ProjectMember.created_at).all()]


@router.get("/projects/{project_id}/eligible-members")
def eligible_project_members(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "members:manage")
    existing = {row.user_id for row in db.query(ProjectMember).filter_by(project_id=project_id).all()}
    return [{"id": user.id, "name": user.name, "email": user.email, "role": user.role, "is_active": user.is_active,
             "created_at": user.created_at} for user in db.query(User).filter_by(is_active=True).order_by(User.name).all() if user.id not in existing]


@router.patch("/projects/{project_id}/members/{member_id}")
def update_member(project_id: int, member_id: int, request: ProjectMemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "members:manage")
    member = db.query(ProjectMember).filter_by(id=member_id, project_id=project_id).first()
    if not member: raise HTTPException(404, "Project member not found")
    if request.user_id != member.user_id: raise HTTPException(400, "A membership cannot be moved to another user")
    member.role = request.project_role
    member.skills_json = json.dumps(sorted({skill.strip().lower() for skill in request.skills if skill.strip()}))
    member.experience_level = request.experience_level; member.current_capacity = request.current_capacity
    db.commit(); return workload(db, member)


@router.get("/projects/{project_id}/team/workload")
def team_workload(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "analytics:view")
    return [workload(db, member) for member in db.query(ProjectMember).filter_by(project_id=project_id, active=True).all()]


@router.post("/tasks/{task_id}/assignment-recommendations")
def recommend_assignment(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter_by(id=task_id).first()
    if not task: raise HTTPException(404, "Task not found")
    require_permission(db, task.project_id, current_user, "assignments:recommend")
    existing = db.query(AssignmentRecommendation).filter_by(task_id=task.id, state="PROPOSED").first()
    if existing: return recommendation_json(existing)
    candidates = score_candidates(db, task)
    qualified = [candidate for candidate in candidates if not candidate["disqualified"]]
    if not qualified: raise HTTPException(422, "No qualified active project member")
    best = qualified[0]
    row = AssignmentRecommendation(project_id=task.project_id, task_id=task.id, recommended_member_id=best["memberId"], score=best["score"],
        score_breakdown_json=json.dumps(best["breakdown"]), reasons_json=json.dumps(best["reasons"]),
        alternatives_json=json.dumps(qualified[1:4]), required_skills_json=json.dumps(required_skills(task)))
    db.add(row); db.flush(); log_activity(db, task.project_id, None, "ASSIGNMENT_RECOMMENDED", "TASK", task.id,
        {"recommendationId": row.id, "memberId": best["memberId"], "score": best["score"]}, actor_type="AGENT"); db.commit()
    return recommendation_json(row)


@router.get("/projects/{project_id}/assignment-recommendations")
def assignment_recommendations(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "analytics:view")
    return [recommendation_json(row) for row in db.query(AssignmentRecommendation).filter_by(project_id=project_id).order_by(AssignmentRecommendation.created_at.desc()).all()]


@router.post("/assignment-recommendations/{recommendation_id}/approve")
def approve_assignment(recommendation_id: int, request: AssignmentApproveRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(AssignmentRecommendation).filter_by(id=recommendation_id).first()
    if not row: raise HTTPException(404, "Assignment recommendation not found")
    require_permission(db, row.project_id, current_user, "assignments:approve")
    if row.state != "PROPOSED": raise HTTPException(409, "Recommendation is no longer awaiting approval")
    selected_id = request.member_id or row.recommended_member_id
    member = db.query(ProjectMember).filter_by(id=selected_id, project_id=row.project_id, active=True).first()
    if not member: raise HTTPException(400, "Selected member is not active in this project")
    task = db.query(Task).filter_by(id=row.task_id, project_id=row.project_id).first()
    if task.assigned_to is not None: raise HTTPException(409, "Task is already assigned")
    task.assigned_to = member.user_id; row.state = "EXECUTED"; row.reviewed_by = current_user.id; row.reviewed_at = datetime.utcnow()
    log_activity(db, row.project_id, current_user.id, "TASK_ASSIGNED", "TASK", task.id, {"memberId": member.id, "userId": member.user_id}); db.commit()
    context = build_assignment_context(db, task.id, row.project_id, member.user_id)
    notification = {"status": "NOT_CONFIGURED"}
    if db.query(GoogleConnection).filter_by(user_id=current_user.id).first():
        notification = send_assignment_email(db, current_user.id, context)
    event = {"SENT": "ASSIGNMENT_EMAIL_SENT", "FAILED": "ASSIGNMENT_EMAIL_FAILED", "DISABLED": "ASSIGNMENT_EMAIL_SKIPPED"}.get(notification["status"], "ASSIGNMENT_EMAIL_SKIPPED")
    log_activity(db, row.project_id, current_user.id, event, "TASK", task.id,
        {"status": notification["status"], "requirementsShared": len(context["requirements"]), "documentsShared": len(context["documents"])}); db.commit()
    for document_id in notification.get("attachments", []):
        log_activity(db, row.project_id, current_user.id, "ASSIGNMENT_DOCUMENT_ATTACHED", "DOCUMENT", document_id, {"taskId": task.id})
    db.commit()
    return {"taskId": task.id, "assignedUserId": task.assigned_to, "recommendation": recommendation_json(row), "notification": notification,
        "contextShared": {"requirements": len(context["requirements"]), "documents": len(context["documents"])}}


@router.get("/tasks/{task_id}/assignment-context")
def assignment_context(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter_by(id=task_id).first()
    if not task or task.assigned_to is None: raise HTTPException(404, "Assigned task not found")
    if task.assigned_to != current_user.id:
        require_permission(db, task.project_id, current_user, "analytics:view")
    context = build_assignment_context(db, task.id, task.project_id, task.assigned_to)
    for document in context["documents"]: document.pop("attachment_path", None)
    return context


@router.post("/tasks/{task_id}/assignment-notification/retry")
def retry_assignment_notification(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter_by(id=task_id).first()
    if not task or task.assigned_to is None: raise HTTPException(404, "Assigned task not found")
    require_permission(db, task.project_id, current_user, "assignments:approve")
    if not db.query(GoogleConnection).filter_by(user_id=current_user.id).first(): raise HTTPException(409, "Approver Google account is not connected")
    context = build_assignment_context(db, task.id, task.project_id, task.assigned_to)
    notification = send_assignment_email(db, current_user.id, context)
    event = "ASSIGNMENT_EMAIL_SENT" if notification["status"] == "SENT" else "ASSIGNMENT_EMAIL_FAILED"
    log_activity(db, task.project_id, current_user.id, event, "TASK", task.id, {"retry": True, "status": notification["status"]}); db.commit()
    return {"taskId": task.id, "notification": notification, "contextShared": {"requirements": len(context["requirements"]), "documents": len(context["documents"])}}


@router.get("/projects/{project_id}/activity")
def activity(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "activity:view")
    rows = db.query(ActivityLog).filter_by(project_id=project_id).order_by(ActivityLog.created_at.desc()).limit(100).all()
    return [{"id": row.id, "actorType": row.actor_type, "actorUserId": row.user_id, "action": row.action,
        "targetType": row.entity_type, "targetId": row.entity_id, "metadata": json.loads(row.details or "{}"), "createdAt": row.created_at} for row in rows]
