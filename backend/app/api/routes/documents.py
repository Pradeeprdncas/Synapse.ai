import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from app.services.assignment_context import validate_download
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.document import Document
from app.models.user import User
from app.services.document_ingestion import ingest_document
from app.services.vector_store import delete_document_chunks
from app.services.rbac import require_permission

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

UPLOAD_DIR = "storage/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


def serialize_document(document):
    return {
        "id": document.id,
        "project_id": document.project_id,
        "uploaded_by": document.uploaded_by,
        "name": document.original_name,
        "original_name": document.original_name,
        "file_type": document.file_type,
        "status": document.processing_status,
        "processing_status": document.processing_status,
        "created_at": document.created_at,
        "processing_error": document.processing_error,
    }


@router.get("/")
def list_documents(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if project_id is None:
        raise HTTPException(400, "project_id is required")
    require_permission(db, project_id, current_user, "project:view")
    require_permission(db, project_id, current_user, "documents:write")
    query = db.query(Document)
    if project_id is not None:
        query = query.filter(Document.project_id == project_id)
    return [serialize_document(document) for document in query.order_by(Document.created_at.desc()).all()]


@router.post("/upload")
def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Authorize before writing any attacker-controlled bytes to disk.
    require_permission(db, project_id, current_user, "documents:write")
    safe_name = os.path.basename(file.filename or "document")
    file_path = f"{UPLOAD_DIR}/{uuid.uuid4().hex}-{safe_name}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = Document(
        project_id=project_id,
        uploaded_by=current_user.id,
        original_name=safe_name,
        file_path=file_path,
        file_type=file.content_type,
        processing_status="PROCESSING"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        ingest_document(db, document)
        document.processing_status = "READY"

    except Exception as exc:
        document.processing_status = "FAILED"
        document.processing_error = str(exc)
    db.commit()
    db.refresh(document)

    return {
        "message": "File uploaded successfully",
        "document": serialize_document(document)
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    require_permission(db, document.project_id, current_user, "documents:write")
    
    # Try to delete the physical file
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception:
            pass # Continue even if file removal fails
    
    delete_document_chunks(document.project_id, document.id)
    db.delete(document)
    db.commit()
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/download")
def download_document(document_id: int, recipient_id: int, expires: int, signature: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter_by(id=document_id).first()
    if not document or not document.file_path or not os.path.isfile(document.file_path): raise HTTPException(404, "Document file not found")
    validate_download(db, document, recipient_id, expires, signature)
    return FileResponse(document.file_path, media_type=document.file_type or "application/octet-stream", filename=document.original_name)
