import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.atlas_agent import GoogleConnection
from app.models.document import Document
from app.models.user import User
from app.services.document_ingestion import ingest_document
from app.services.google_integration import config, create_authorization, exchange_code, fetch_google_doc
from app.services.rbac import require_permission

router = APIRouter(prefix="/google", tags=["Google"])

class GoogleDocImport(BaseModel):
    document_id: str = Field(min_length=3, max_length=200)

@router.get("/oauth/start")
def oauth_start(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"authorizationUrl": create_authorization(db, current_user.id)}

@router.get("/oauth/callback")
def oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    exchange_code(db, state, code)
    return RedirectResponse(config()["success_url"], status_code=302)

@router.get("/connection")
def connection(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(GoogleConnection).filter_by(user_id=current_user.id).first()
    return {"connected": bool(row), "email": row.email if row else None, "scopes": [] if not row else __import__("json").loads(row.scopes_json)}

@router.delete("/connection")
def disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(GoogleConnection).filter_by(user_id=current_user.id).first()
    if row: db.delete(row); db.commit()
    return {"connected": False}

@router.post("/projects/{project_id}/docs/import")
def import_doc(project_id: int, request: GoogleDocImport, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(db, project_id, current_user, "documents:write")
    title, text = fetch_google_doc(db, current_user.id, request.document_id)
    safe_name = "google-doc-" + request.document_id[:24] + "-" + __import__("uuid").uuid4().hex + ".txt"; path = os.path.join("storage", "uploads", safe_name)
    with open(path, "w", encoding="utf-8") as target: target.write(text)
    row = Document(project_id=project_id, uploaded_by=current_user.id, original_name=title, file_path=path, file_type="application/vnd.google-apps.document", processing_status="READY",
        source_provider="GOOGLE_DOCS", source_url=f"https://docs.google.com/document/d/{request.document_id}/edit")
    db.add(row); db.flush()
    chunks = ingest_document(db, row, text)
    db.commit(); db.refresh(row)
    return {"documentId": row.id, "name": title, "chunksDetected": chunks}
