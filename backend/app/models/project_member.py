from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, ForeignKey, String, Text, UniqueConstraint
from app.core.database import Base


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member_user"),)

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"))

    user_id = Column(Integer, ForeignKey("users.id"))

    role = Column(String, default="MEMBER")

    skills_json = Column(Text, default="[]", nullable=False)
    experience_level = Column(String, default="STANDARD", nullable=False)
    current_capacity = Column(Float, default=1.0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
