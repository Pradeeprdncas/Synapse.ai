"""HTTP-level Atlas demo verification against an isolated DATABASE_URL."""
import os
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PASSWORD = "temporary-demo-password"

def register(name, email):
    response = client.post("/auth/register", json={"name": name, "email": email, "password": PASSWORD}); assert response.status_code == 200, response.text
    login = client.post("/auth/login", json={"email": email, "password": PASSWORD}); assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return headers, client.get("/auth/me", headers=headers).json()["id"]

def main():
    manager_headers, _ = register("Maya", "maya.flow@example.test")
    project_response = client.post("/projects/", headers=manager_headers, json={"name": "Atlas Flow", "description": "Verification"}); assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()["id"]
    team = [
        ("Arun", "TEAM_LEAD", ["python", "fastapi", "postgresql", "architecture"]),
        ("Priya", "SENIOR_DEVELOPER", ["react", "apis", "authentication"]),
        ("Kumar", "JUNIOR_DEVELOPER", ["python", "react", "testing"]),
        ("Nila", "INTERN", ["documentation", "testing", "frontend"]),
    ]
    role_headers = {}
    for name, role, skills in team:
        headers, user_id = register(name, f"{name.lower()}.flow@example.test"); role_headers[role] = headers
        response = client.post(f"/projects/{project_id}/members", headers=manager_headers, json={"user_id": user_id, "project_role": role, "skills": skills}); assert response.status_code == 200, response.text
    demo = Path(__file__).parents[2] / "demo" / "atlas-agent-sample-prd.md"
    with demo.open("rb") as source:
        upload = client.post(f"/documents/upload?project_id={project_id}", headers=manager_headers, files={"file": (demo.name, source, "text/markdown")})
    assert upload.status_code == 200 and upload.json()["document"]["processing_status"] == "READY", upload.text
    analyzed = client.post(f"/projects/{project_id}/agent/analyze", headers=manager_headers); assert analyzed.status_code == 200, analyzed.text
    proposals = client.get(f"/projects/{project_id}/task-proposals", headers=manager_headers).json(); assert proposals
    approved = client.post(f"/task-proposals/{proposals[0]['id']}/approve", headers=manager_headers); assert approved.status_code == 200, approved.text
    task_id = approved.json()["createdTaskId"]
    recommendation = client.post(f"/tasks/{task_id}/assignment-recommendations", headers=manager_headers); assert recommendation.status_code == 200, recommendation.text
    assignment = client.post(f"/assignment-recommendations/{recommendation.json()['id']}/approve", headers=manager_headers, json={}); assert assignment.status_code == 200, assignment.text
    context = client.get(f"/tasks/{task_id}/assignment-context", headers=manager_headers); assert context.status_code == 200, context.text
    assert context.json()["requirements"] and len(context.json()["documents"]) == 1
    assert assignment.json()["contextShared"] == {"requirements": 1, "documents": 1}
    duplicate = client.post(f"/assignment-recommendations/{recommendation.json()['id']}/approve", headers=manager_headers, json={}); assert duplicate.status_code == 409
    assert client.get(f"/projects/{project_id}/health", headers=manager_headers).status_code == 200
    assert client.get(f"/projects/{project_id}/activity", headers=manager_headers).json()
    assert client.get(f"/tasks/project/{project_id}", headers=role_headers["INTERN"]).json() == []
    print({"projectId": project_id, "requirements": analyzed.json()["requirementsCreated"], "proposals": len(proposals), "assignedTaskId": task_id, "contextRequirements": len(context.json()["requirements"]), "contextDocuments": len(context.json()["documents"]), "notification": assignment.json()["notification"]["status"], "duplicateAssignmentStatus": duplicate.status_code, "rolesVerified": 5})
    from app.services import vector_store
    if vector_store._client: vector_store._client.close(); vector_store._client = None

if __name__ == "__main__": main()
