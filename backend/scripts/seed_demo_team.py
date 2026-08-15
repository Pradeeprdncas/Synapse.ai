"""Create the five-member Atlas demo team. Requires ATLAS_DEMO_PASSWORD; never uses a production default."""
import json
import os
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User

TEAM = [
    ("Maya", "maya.demo@example.test", "MANAGER", ["product", "architecture"]),
    ("Arun", "arun.demo@example.test", "TEAM_LEAD", ["python", "fastapi", "postgresql", "system design"]),
    ("Priya", "priya.demo@example.test", "SENIOR_DEVELOPER", ["react", "node.js", "apis", "authentication"]),
    ("Kumar", "kumar.demo@example.test", "JUNIOR_DEVELOPER", ["python", "react", "testing"]),
    ("Nila", "nila.demo@example.test", "INTERN", ["documentation", "testing", "frontend"]),
]

def main():
    if len(sys.argv) != 2: raise SystemExit("Usage: python scripts/seed_demo_team.py PROJECT_ID")
    password = os.getenv("ATLAS_DEMO_PASSWORD")
    if not password or len(password) < 10: raise SystemExit("Set ATLAS_DEMO_PASSWORD to at least 10 characters")
    project_id = int(sys.argv[1]); db = SessionLocal()
    try:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project: raise SystemExit("Project not found")
        for name, email, role, skills in TEAM:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                user = User(name=name, email=email, password=hash_password(password), role="MEMBER"); db.add(user); db.flush()
            membership = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user.id).first()
            if not membership:
                membership = ProjectMember(project_id=project_id, user_id=user.id); db.add(membership)
            membership.role = role; membership.skills_json = json.dumps(skills); membership.active = True
        db.commit(); print(f"Created/updated five demo members for project {project_id} using fake example.test emails.")
    finally: db.close()

if __name__ == "__main__": main()
