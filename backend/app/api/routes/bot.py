from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    UploadFile,
    File,
    Form
)

from pydantic import BaseModel

from app.services.rag_service import (
    query_rag,
    ingest_text_to_rag
)

from app.config import settings

router = APIRouter(
    prefix="/bot",
    tags=["Bot"]
)

# -----------------------------------
# REQUEST MODEL
# -----------------------------------

class BotChatRequest(BaseModel):
    question: str
    project_id: str

# -----------------------------------
# VERIFY BOT
# -----------------------------------

def verify_bot(secret: str):

    if secret != settings.BOT_SECRET_KEY:

        raise HTTPException(
            status_code=401,
            detail="Invalid bot secret"
        )

# -----------------------------------
# CHAT ROUTE
# -----------------------------------

@router.post("/chat")
async def bot_chat(
    request: BotChatRequest,
    x_bot_secret: str = Header(None)
):

    verify_bot(x_bot_secret)

    response = await query_rag(
        question=request.question,
        project_id=request.project_id,
        collection_name=f"telegram_{request.project_id}"
    )

    return response

# -----------------------------------
# UPLOAD ROUTE
# -----------------------------------

@router.post("/upload")
async def bot_upload(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    x_bot_secret: str = Header(None)
):

    verify_bot(x_bot_secret)

    content = await file.read()

    try:

        text = content.decode(
            "utf-8",
            errors="ignore"
        )

    except Exception:

        text = str(content)

    response = await ingest_text_to_rag(
        text=text,
        filename=file.filename,
        project_id=project_id,
        collection_name=f"telegram_{project_id}"
    )

    return response
