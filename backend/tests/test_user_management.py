import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.admin import create_managed_project, create_user, list_users
from app.api.routes.auth import update_me
from app.core.database import Base
from app.core.security import hash_password, require_admin, verify_password
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.user import AdminUserCreate, ProfileUpdate
from app.services.rbac import require_permission


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_only_application_admin_can_manage_users(db):
    admin = User(name="Admin", email="admin@example.test", password=hash_password("password"), role="ADMIN")
    member = User(name="Member", email="member@example.test", password=hash_password("password"), role="MEMBER")
    db.add_all([admin, member]); db.commit()
    assert require_admin(admin) is admin
    with pytest.raises(HTTPException) as denied: require_admin(member)
    assert denied.value.status_code == 403
    assert len(list_users(db, admin)) == 2


def test_admin_creates_admin_and_assigns_project_manager(db):
    admin = User(name="Admin", email="admin@example.test", password=hash_password("password"), role="ADMIN")
    db.add(admin); db.commit()
    made = create_user(AdminUserCreate(name="Second Admin", email="second@example.test", password="1234567", role="ADMIN", send_email=False), db, admin)
    assert made["role"] == "ADMIN" and made["credential_email_status"] == "SKIPPED"
    project = create_managed_project("Managed", made["id"], "Demo", db, admin)
    membership = db.query(ProjectMember).filter_by(project_id=project["id"], user_id=made["id"]).one()
    assert membership.role == "MANAGER"
    require_permission(db, project["id"], admin, "members:manage")


def test_user_changes_profile_and_password_with_current_password(db):
    user = User(name="Before", email="before@example.test", password=hash_password("oldpass1"), role="MEMBER")
    db.add(user); db.commit()
    result = update_me(ProfileUpdate(name="After", email="after@example.test", current_password="oldpass1", new_password="newpass1"), db, user)
    assert result["name"] == "After" and result["email"] == "after@example.test"
    assert verify_password("newpass1", user.password)
    with pytest.raises(HTTPException):
        update_me(ProfileUpdate(current_password="wrong", new_password="newpass2"), db, user)
