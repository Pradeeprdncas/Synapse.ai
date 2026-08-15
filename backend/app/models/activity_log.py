from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text
)

from datetime import datetime

from app.core.database import Base


class ActivityLog(Base):

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id")
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    action = Column(String)

    entity_type = Column(String)

    entity_id = Column(Integer)

    details = Column(Text)
    actor_type = Column(String, default="USER", nullable=False)
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
