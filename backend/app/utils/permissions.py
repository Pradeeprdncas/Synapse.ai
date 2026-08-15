from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.models.project import Project


def check_project_access(
    db: Session,
    project_id: int,
    user_id: int
):

    project = db.query(Project).filter(Project.id == project_id).first()
    if project and project.owner_id == user_id:
        return None
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.active == True,
    ).first()

    if not member:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return member
