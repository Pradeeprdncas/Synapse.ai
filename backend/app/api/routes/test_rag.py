from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.rag.keyword_rag import keyword_search
from app.services.rbac import require_permission

router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)

class RagSearchRequest(BaseModel):
    query: str
    project_id: int | None = None


@router.get("/search")
def search_rag(project_id: int, query: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    require_permission(db, project_id, current_user, "project:view")

    results = keyword_search(project_id, query)

    return {
        "results": results
    }


@router.post("/search")
def search_rag_post(payload: RagSearchRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.project_id is None:
        return {"results": []}

    require_permission(db, payload.project_id, current_user, "project:view")

    results = keyword_search(payload.project_id, payload.query)

    return {
        "results": results
    }
