from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatRequest
from app.services.chat.chat_service import generate_chat_response
from app.services.chat.chat_memory import get_chat_history

from app.core.security import get_current_user
from app.models.user import User
from app.services.rbac import require_permission

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/{project_id}")
def chat_with_project(
    project_id: int,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_permission(db, project_id, current_user, "project:view")
    return generate_chat_response(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        query=body.query
    )

@router.get("/history/{project_id}")
def chat_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, project_id, current_user, "project:view")
    history = get_chat_history(db, project_id)

    return history
