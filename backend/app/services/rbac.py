from enum import Enum

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User


class ProjectRole(str, Enum):
    MANAGER = "MANAGER"
    TEAM_LEAD = "TEAM_LEAD"
    SENIOR_DEVELOPER = "SENIOR_DEVELOPER"
    JUNIOR_DEVELOPER = "JUNIOR_DEVELOPER"
    INTERN = "INTERN"


PERMISSIONS = {
    ProjectRole.MANAGER: {"project:view", "requirements:view", "documents:write", "agent:run", "proposal:review", "tasks:create", "tasks:update:any", "tasks:delete", "assignments:recommend", "assignments:approve", "members:manage", "analytics:view", "activity:view"},
    ProjectRole.TEAM_LEAD: {"project:view", "requirements:view", "proposal:view", "tasks:create", "tasks:update:any", "assignments:recommend", "assignments:approve", "analytics:view", "activity:view"},
    ProjectRole.SENIOR_DEVELOPER: {"project:view", "requirements:view", "proposal:view", "tasks:view:related", "tasks:update:own", "activity:view"},
    ProjectRole.JUNIOR_DEVELOPER: {"project:view", "requirements:view:assigned", "tasks:view:own", "tasks:update:own"},
    ProjectRole.INTERN: {"project:view", "requirements:view:assigned", "tasks:view:own", "tasks:update:own:limited"},
}


def membership_for(db: Session, project_id: int, user: User) -> tuple[Project, ProjectMember | None, ProjectRole]:
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    membership = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user.id, active=True).first()
    if user.role == "ADMIN":
        return project, membership, ProjectRole.MANAGER
    if project.owner_id == user.id:
        return project, membership, ProjectRole.MANAGER
    if not membership:
        raise HTTPException(403, "Active project membership required")
    try:
        return project, membership, ProjectRole(membership.role)
    except ValueError:
        raise HTTPException(403, "Project membership role is not authorized")


def require_permission(db: Session, project_id: int, user: User, permission: str):
    project, membership, role = membership_for(db, project_id, user)
    if permission not in PERMISSIONS[role]:
        raise HTTPException(403, f"{role.value} cannot perform {permission}")
    return project, membership, role
