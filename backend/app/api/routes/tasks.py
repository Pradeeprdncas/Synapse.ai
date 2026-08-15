from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.services.rbac import require_permission, membership_for

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

def serialize_checklist(item):
    return {
        "id": item.id,
        "title": item.title,
        "label": item.title,
        "is_completed": item.is_completed,
        "done": item.is_completed,
    }


def serialize_task(task):
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "module_id": task.module_id,
        "assigned_to": task.assigned_to,
        "complexity": task.complexity,
        "created_at": task.created_at,
        "checklist": [serialize_checklist(item) for item in task.checklists],
    }


@router.post("/")
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, task.project_id, current_user, "tasks:create")

    new_task = Task(
        project_id=task.project_id,
        title=task.title,
        description=task.description
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return serialize_task(new_task)


@router.get("/")
def get_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    owned = [row.id for row in db.query(Project).filter_by(owner_id=current_user.id).all()]
    memberships = db.query(ProjectMember).filter_by(user_id=current_user.id, active=True).all()
    broad = set(owned + [row.project_id for row in memberships if row.role in ("MANAGER", "TEAM_LEAD", "SENIOR_DEVELOPER")])
    limited = {row.project_id for row in memberships if row.role in ("JUNIOR_DEVELOPER", "INTERN")}
    tasks = []
    if broad:
        tasks.extend(db.query(Task).filter(Task.project_id.in_(broad)).all())
    if limited:
        tasks.extend(db.query(Task).filter(Task.project_id.in_(limited), Task.assigned_to == current_user.id).all())
    return [serialize_task(task) for task in sorted({task.id: task for task in tasks}.values(), key=lambda row: row.id)]


@router.get("/project/{project_id}")
def get_project_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, _, role = membership_for(db, project_id, current_user)
    query = db.query(Task).filter(
        Task.project_id == project_id
    )
    if role.value in ("JUNIOR_DEVELOPER", "INTERN"):
        query = query.filter(Task.assigned_to == current_user.id)
    tasks = query.all()

    return [serialize_task(task) for task in tasks]


@router.patch("/{task_id}")
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    _, _, role = membership_for(db, task.project_id, current_user)
    update_data = task_update.model_dump(exclude_unset=True)
    if role.value in ("SENIOR_DEVELOPER", "JUNIOR_DEVELOPER", "INTERN"):
        if task.assigned_to != current_user.id: raise HTTPException(403, "Only assigned work can be updated")
        allowed = {"status"}
        if set(update_data) - allowed: raise HTTPException(403, "This project role can only update task status")
        if role.value == "INTERN" and update_data.get("status") not in ("TODO", "IN_PROGRESS", "DONE"):
            raise HTTPException(403, "Intern status transition is not permitted")
    else:
        require_permission(db, task.project_id, current_user, "tasks:update:any")
    for key, value in update_data.items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    require_permission(db, task.project_id, current_user, "tasks:delete")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}
