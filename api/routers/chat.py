"""POST /chat/message, POST /chat/message/stream, POST /chat/voice, GET /chat/history"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_ai_service, get_bot_shim
from api.schemas.chat import ChatMessageIn, ChatResponse, ChatMessageOut
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/message", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def send_message(
    request: Request,
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


@router.post("/message/stream")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def send_message_stream(
    request: Request,
    body: ChatMessageIn,
    user_key: Annotated[str, Depends(get_current_user)],
    ai_svc=Depends(get_ai_service),
    bot_shim=Depends(get_bot_shim),
):
    """SSE-Streaming endpoint for chat messages."""

    # Intent-Pre-Check: bei erkanntem Service-Intent den Handler-Pfad nutzen
    intent_data = await ai_svc._detect_intent(body.message, user_key)
    intent = intent_data.get("intent", "chat")

    if intent != "chat":
        async def handler_generator():
            try:
                result = await ai_svc.process_message(
                    message=body.message,
                    user_key=user_key,
                    chat_id=0,
                    bot=bot_shim,
                )
                yield f"data: {json.dumps({'token': result})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                logger.error("Handler-Fehler für '%s' (intent=%s): %s", user_key, intent, e)
                yield f"data: {json.dumps({'error': 'Entschuldigung, es ist ein interner Fehler aufgetreten.'})}\n\n"

        return StreamingResponse(
            handler_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Standard-Streaming-Pfad für reinen Chat
    intelligence = ai_svc.intelligence

    async def event_generator():
        try:
            async for chunk in intelligence.process_with_memory_stream(body.message, user_key):
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error("Streaming-Fehler für '%s': %s", user_key, e)
            yield f"data: {json.dumps({'error': 'Entschuldigung, es ist ein interner Fehler aufgetreten.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/voice")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def send_voice_message(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    ai_svc=Depends(get_ai_service),
    file: UploadFile = File(...),
):
    """Empfängt Audio, transkribiert via Whisper, gibt Text zurück."""
    content = await file.read()
    max_audio = 10 * 1024 * 1024  # 10 MB
    if len(content) > max_audio:
        raise HTTPException(status_code=413, detail="Audio zu groß (max 10 MB)")

    text = await ai_svc.transcribe_voice(content, filename=file.filename or "voice.webm")
    if not text:
        raise HTTPException(status_code=422, detail="Transkription fehlgeschlagen – bitte erneut versuchen.")

    return {"transcription": text}


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
        result = [
            ChatMessageOut(
                id=r.id,
                role=r.role,
                content=r.content,
                created_at=r.created_at,
            )
            for r in reversed(rows)
        ]
    return result
