from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.checklist import ChecklistItem
from app.models.task import Task
from app.models.user import User
from app.services.rbac import membership_for, require_permission
from app.schemas.checklist import ChecklistCreate, ChecklistUpdate

router = APIRouter(
    prefix="/checklists",
    tags=["Checklists"]
)

def serialize_checklist(item):
    return {
        "id": item.id,
        "task_id": item.task_id,
        "title": item.title,
        "label": item.title,
        "is_completed": item.is_completed,
        "done": item.is_completed,
    }


@router.post("/")
def create_checklist(
    checklist: ChecklistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter_by(id=checklist.task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    _, _, role = membership_for(db, task.project_id, current_user)
    if role.value in ("SENIOR_DEVELOPER", "JUNIOR_DEVELOPER", "INTERN"):
        if task.assigned_to != current_user.id:
            raise HTTPException(403, "Only assigned work can be updated")
    else:
        require_permission(db, task.project_id, current_user, "tasks:update:any")

    item = ChecklistItem(
        task_id=checklist.task_id,
        title=checklist.title
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return serialize_checklist(item)


@router.get("/{task_id}")
def get_task_checklists(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    _, _, role = membership_for(db, task.project_id, current_user)
    if role.value in ("JUNIOR_DEVELOPER", "INTERN") and task.assigned_to != current_user.id:
        raise HTTPException(403, "Only assigned work is visible")

    items = db.query(ChecklistItem).filter(
        ChecklistItem.task_id == task_id
    ).all()

    return [serialize_checklist(item) for item in items]


@router.patch("/{item_id}")
def update_checklist(
    item_id: int,
    checklist_update: ChecklistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    task = db.query(Task).filter_by(id=item.task_id).first()
    _, _, role = membership_for(db, task.project_id, current_user)
    if role.value in ("SENIOR_DEVELOPER", "JUNIOR_DEVELOPER", "INTERN"):
        if task.assigned_to != current_user.id:
            raise HTTPException(403, "Only assigned work can be updated")
    else:
        require_permission(db, task.project_id, current_user, "tasks:update:any")
    
    update_data = checklist_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    db.commit()
    db.refresh(item)
    return serialize_checklist(item)


@router.delete("/{item_id}")
def delete_checklist(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    task = db.query(Task).filter_by(id=item.task_id).first()
    require_permission(db, task.project_id, current_user, "tasks:delete")
    
    db.delete(item)
    db.commit()
    return {"message": "Checklist item deleted successfully"}
