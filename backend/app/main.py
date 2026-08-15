from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import Base, engine

from app.models import *

from app.api.routes.auth import router as auth_router
from app.api.routes.projects import router as project_router
from app.api.routes.tasks import router as task_router
from app.api.routes.documents import router as document_router
from app.api.routes.checklist import router as checklist_router
from app.api.routes.test_ai import router as test_ai_router
from app.api.routes.test_rag import router as rag_router
from app.api.routes.ai import router as ai_router
import app.models

from app.api.routes.chat import router as chat_router
from app.api.routes.bot import router as bot_router
from app.api.routes.atlas_agent import router as atlas_agent_router
from app.api.routes.google import router as google_router
from app.api.routes.admin import router as admin_router





app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://synapse-ai.pradeep-nagarajan.workers.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def ensure_sqlite_schema():
    if engine.dialect.name != "sqlite":
        return

    required_columns = {
        "tasks": {
            "module_id": "INTEGER",
            "complexity": "VARCHAR DEFAULT 'STANDARD'",
        },
        "documents": {
            "processing_status": "VARCHAR DEFAULT 'UPLOADED'",
            "processing_error": "TEXT",
            "source_provider": "VARCHAR",
            "source_url": "VARCHAR",
        },
        "project_members": {
            "skills_json": "TEXT DEFAULT '[]'",
            "experience_level": "VARCHAR DEFAULT 'STANDARD'",
            "current_capacity": "FLOAT DEFAULT 1.0",
            "active": "BOOLEAN DEFAULT 1",
            "created_at": "DATETIME",
        },
        "activity_logs": {"actor_type": "VARCHAR DEFAULT 'USER'"},
    }

    with engine.begin() as connection:
        for table, columns in required_columns.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            for column, definition in columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


ensure_sqlite_schema()

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(task_router)
app.include_router(document_router)
app.include_router(checklist_router)
app.include_router(test_ai_router)
app.include_router(rag_router)
app.include_router(ai_router)
app.include_router(bot_router)
app.include_router(chat_router)
app.include_router(atlas_agent_router)
app.include_router(google_router)
app.include_router(admin_router)





@app.get("/")
def home():
    return {
        "message": "RAG CRM Backend Running"
    }
