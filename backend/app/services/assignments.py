import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User

ROLE_FIT = {
    "COMPLEX": {"TEAM_LEAD": 25, "SENIOR_DEVELOPER": 24, "JUNIOR_DEVELOPER": 8, "INTERN": 0, "MANAGER": 18},
    "STANDARD": {"TEAM_LEAD": 21, "SENIOR_DEVELOPER": 25, "JUNIOR_DEVELOPER": 21, "INTERN": 8, "MANAGER": 12},
    "SIMPLE": {"TEAM_LEAD": 12, "SENIOR_DEVELOPER": 17, "JUNIOR_DEVELOPER": 25, "INTERN": 23, "MANAGER": 6},
}
SKILL_ALIASES = {"auth": "authentication", "postgres": "postgresql", "api": "apis", "test": "testing", "docs": "documentation"}
SENSITIVE = {"security", "authentication", "authorization", "payment", "architecture", "permissions"}


def required_skills(task: Task) -> list[str]:
    text = f"{task.title} {task.description or ''}".lower()
    candidates = ["python", "fastapi", "postgresql", "react", "node.js", "apis", "authentication", "security", "testing", "documentation", "frontend", "architecture"]
    found = [skill for skill in candidates if skill in text]
    return found or (["testing"] if task.complexity == "SIMPLE" else [])


def classify_complexity(priority: str, description: str, dependencies: list[str] | None = None, acceptance_count: int = 0) -> str:
    text = description.lower(); score = 0
    score += {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 1, "LOW": 0}.get(priority.upper(), 1)
    score += min(len(dependencies or []), 3)
    score += min(acceptance_count // 3, 2)
    score += 3 if any(term in text for term in SENSITIVE) else 0
    score += 2 if any(term in text for term in ("migration", "external api", "webhook", "system design")) else 0
    return "COMPLEX" if score >= 6 else "STANDARD" if score >= 3 else "SIMPLE"


def workload(db: Session, member: ProjectMember) -> dict:
    tasks = db.query(Task).filter_by(project_id=member.project_id, assigned_to=member.user_id).all()
    active = [task for task in tasks if task.status.upper() not in ("DONE", "COMPLETED", "CANCELLED")]
    high = [task for task in active if task.priority.upper() in ("HIGH", "CRITICAL")]
    completed = len(tasks) - len(active)
    ratio = min(1.0, len(active) / max(1.0, 5.0 * member.current_capacity))
    label = "HIGH" if ratio >= .8 else "MEDIUM" if ratio >= .4 else "AVAILABLE"
    user = db.query(User).filter_by(id=member.user_id).first()
    return {"memberId": member.id, "userId": member.user_id, "name": user.name if user else "Unknown",
        "email": user.email if user else None, "projectRole": member.role, "skills": json.loads(member.skills_json or "[]"),
        "assignedTasks": len(tasks), "activeTasks": len(active), "highPriorityTasks": len(high),
        "completedTasks": completed, "capacity": member.current_capacity, "workloadIndicator": label}


def score_candidates(db: Session, task: Task):
    skills = required_skills(task); sensitive = bool(set(skills) & SENSITIVE)
    scored = []
    for member in db.query(ProjectMember).filter_by(project_id=task.project_id, active=True).all():
        profile = workload(db, member); member_skills = {SKILL_ALIASES.get(x.lower(), x.lower()) for x in profile["skills"]}
        matches = sum(1 for skill in skills if SKILL_ALIASES.get(skill, skill) in member_skills)
        skill_score = round(40 * matches / max(1, len(skills)))
        role_score = ROLE_FIT[task.complexity].get(member.role, 0)
        capacity_score = max(0, 20 - profile["activeTasks"] * 4 - profile["highPriorityTasks"] * 4)
        dependency_score = 10 if matches and skills else 5
        priority_score = 5 if task.priority.upper() not in ("HIGH", "CRITICAL") or member.role in ("MANAGER", "TEAM_LEAD", "SENIOR_DEVELOPER") else 0
        disqualified = sensitive and member.role == "INTERN"
        total = 0 if disqualified else min(100, skill_score + role_score + capacity_score + dependency_score + priority_score)
        reasons = [f"{matches}/{len(skills)} required skills matched" if skills else "No specialist skill requirement", f"{member.role} role fit for {task.complexity} work", f"{profile['activeTasks']} active and {profile['highPriorityTasks']} high-priority tasks"]
        if disqualified: reasons.append("Interns are excluded from security/auth/payment/architecture work")
        scored.append({"memberId": member.id, "userId": member.user_id, "name": profile["name"], "projectRole": member.role,
            "score": total, "breakdown": {"skillMatch": skill_score, "roleFit": role_score, "capacity": capacity_score, "dependencyFit": dependency_score, "priorityFit": priority_score},
            "reasons": reasons, "workload": profile, "disqualified": disqualified})
    return sorted(scored, key=lambda item: (-item["score"], item["memberId"]))
