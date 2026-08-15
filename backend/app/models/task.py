from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from datetime import datetime
from app.core.database import Base
from sqlalchemy.orm import relationship
from app.models.checklist import ChecklistItem

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"))

    assigned_to = Column(Integer, ForeignKey("users.id"))

    title = Column(String, nullable=False)

    description = Column(Text)

    status = Column(String, default="TODO")

    priority = Column(String, default="MEDIUM")

    complexity = Column(String, default="STANDARD", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    module_id = Column(Integer,ForeignKey("modules.id"),nullable=True)
    
    checklists = relationship("ChecklistItem",backref="task",cascade="all, delete")
