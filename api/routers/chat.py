"""POST /chat/message, GET /chat/history"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, get_ai_service, get_bot_shim
from api.schemas.chat import ChatMessageIn, ChatResponse, ChatMessageOut

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatMessageIn,
    user_key: Annotated[str, Depends(get_current_user)],
    ai_svc=Depends(get_ai_service),
    bot_shim=Depends(get_bot_shim),
):
    """Sendet eine Nachricht an den KI-Assistenten und gibt die Antwort zurück."""
    try:
        response = await ai_svc.process_message(
            message=body.message,
            user_key=user_key,
            chat_id=0,
            bot=bot_shim,
        )
        return ChatResponse(response=response or "", user_message=body.message)
    except Exception as e:
        logger.error("Chat-Fehler für '%s': %s", user_key, e)
        return ChatResponse(
            response="Entschuldigung, ich konnte deine Nachricht nicht verarbeiten.",
            user_message=body.message,
        )


@router.get("/history", response_model=list[ChatMessageOut])
async def get_history(
    user_key: Annotated[str, Depends(get_current_user)],
    limit: int = 50,
):
    """Gibt die letzten N Chat-Nachrichten aus der DB zurück."""
    from src.services.database import ConversationHistory, get_db

    with get_db()() as session:
        rows = (
            session.query(ConversationHistory)
            .filter_by(user_key=user_key)
            .order_by(ConversationHistory.created_at.desc())
            .limit(limit)
            .all()
        )
    return [
        ChatMessageOut(
            id=r.id,
            role=r.role,
            content=r.content,
            created_at=r.created_at,
        )
        for r in reversed(rows)
    ]
