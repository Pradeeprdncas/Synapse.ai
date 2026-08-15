from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_admin
from app.models.atlas_agent import GoogleConnection
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.user import AdminUserCreate, AdminUserUpdate
from app.services.google_integration import send_gmail_message

router = APIRouter(prefix="/admin", tags=["Administration"])


def user_json(user: User):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role,
            "is_active": user.is_active, "created_at": user.created_at}


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [user_json(row) for row in db.query(User).order_by(User.name, User.id).all()]


@router.post("/users", status_code=201)
def create_user(payload: AdminUserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.query(User).filter_by(email=payload.email).first():
        raise HTTPException(409, "Email already exists")
    user = User(name=payload.name.strip(), email=payload.email, password=hash_password(payload.password), role=payload.role)
    db.add(user); db.commit(); db.refresh(user)
    delivery = "SKIPPED"
    if payload.send_email and db.query(GoogleConnection).filter_by(user_id=admin.id).first():
        message = EmailMessage()
        message["To"] = user.email
        message["Subject"] = "Atlas CRM — Your account has been created"
        message.set_content(
            f"Hi {user.name},\n\nAn Atlas CRM account has been created for you.\n\n"
            f"Email: {user.email}\nTemporary password: {payload.password}\n\n"
            "Please sign in and change your password from Settings.\n"
        )
        delivery = send_gmail_message(db, admin.id, message)["status"]
    return {**user_json(user), "credential_email_status": delivery}


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: AdminUserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user: raise HTTPException(404, "User not found")
    values = payload.model_dump(exclude_unset=True)
    if values.get("email") and values["email"] != user.email:
        if db.query(User).filter(User.email == values["email"], User.id != user.id).first(): raise HTTPException(409, "Email already exists")
        user.email = values["email"]
    for field in ("name", "role", "is_active"):
        if field in values: setattr(user, field, values[field])
    if values.get("password"): user.password = hash_password(values["password"])
    if user.id == admin.id and user.role != "ADMIN": raise HTTPException(400, "You cannot remove your own administrator role")
    db.commit(); db.refresh(user); return user_json(user)


@router.post("/projects", status_code=201)
def create_managed_project(name: str, manager_user_id: int, description: str | None = None,
                           db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    manager = db.query(User).filter_by(id=manager_user_id, is_active=True).first()
    if not manager: raise HTTPException(404, "Active manager user not found")
    project = Project(name=name.strip(), description=description, owner_id=manager.id)
    db.add(project); db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=manager.id, role="MANAGER")); db.commit(); db.refresh(project)
    delivery = "SKIPPED"
    if db.query(GoogleConnection).filter_by(user_id=admin.id).first():
        message = EmailMessage(); message["To"] = manager.email; message["Subject"] = f"Atlas CRM — Project assigned: {project.name}"
        message.set_content(f"Hi {manager.name},\n\nYou are the manager for the Atlas project “{project.name}”.\n\nSign in to Atlas to add team members and manage work.\n")
        delivery = send_gmail_message(db, admin.id, message)["status"]
    return {"id": project.id, "name": project.name, "description": project.description, "manager_user_id": manager.id, "notification_status": delivery}
