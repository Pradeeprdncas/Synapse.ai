from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from app.core.database import Base
from sqlalchemy import Text


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"))

    uploaded_by = Column(Integer, ForeignKey("users.id"))

    original_name = Column(String)

    file_path = Column(String)

    file_type = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)

    processing_status = Column(String,default="UPLOADED")

    processing_error = Column(Text,nullable=True)

    source_provider = Column(String, nullable=True)

    source_url = Column(String, nullable=True)
