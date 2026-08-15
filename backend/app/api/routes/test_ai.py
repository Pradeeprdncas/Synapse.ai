from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User

from app.services.ai.mistral_service import (
    generate_project_structure
)

router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)


@router.get("/generate")
def generate_ai(current_user: User = Depends(get_current_user)):

    sample_text = """
    Create authentication module,
    dashboard module,
    task management system,
    notification service
    """

    result = generate_project_structure(sample_text)

    return {
        "result": result
    }
