import json
import uuid
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import Base, SessionLocal, engine, get_db
from app.models import Conversation, Message
from app.schemas import ChatRequest, ConversationOut, MessageOut
from app.services.ai.router import model_router
from app.services.ai.instructions import build_system_instruction

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Afromind Intelligence API — powered by LUNA AI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "afromind-intelligence",
        "assistant": "LUNA AI",
    }

@app.get("/api/conversations", response_model=list[ConversationOut])
def list_conversations(owner_id: str, db: Session = Depends(get_db)):
    return db.query(Conversation).filter(Conversation.owner_id == owner_id).order_by(Conversation.updated_at.desc()).all()

@app.get("/api/conversations/{conversation_id}", response_model=list[MessageOut])
def get_messages(conversation_id: str, owner_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter_by(id=conversation_id, owner_id=owner_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation.messages

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, owner_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter_by(id=conversation_id, owner_id=owner_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    db.commit()
    return {"deleted": True}

@app.post("/api/chat")
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    if payload.conversation_id:
        conversation = db.query(Conversation).filter_by(
            id=payload.conversation_id, owner_id=payload.owner_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            owner_id=payload.owner_id,
            title=payload.message[:60].strip() or "New conversation",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    conversation_id = conversation.id
    user_message = Message(
        id=str(uuid.uuid4()), conversation_id=conversation_id,
        role="user", content=payload.message,
    )
    db.add(user_message)
    db.commit()

    prior_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history = [{
        "role": "system",
        "content": build_system_instruction(),
    }]
    history.extend([{"role": m.role, "content": m.content} for m in prior_messages])

    async def event_stream():
        full_response = ""
        try:
            provider = model_router.get_provider(settings.ai_provider)
            yield f"event: meta\ndata: {json.dumps({'conversation_id': conversation_id, 'model': payload.model or settings.ai_model})}\n\n"
            async for token in provider.stream_chat(history, payload.model):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            with SessionLocal() as session:
                assistant = Message(
                    id=str(uuid.uuid4()), conversation_id=conversation_id,
                    role="assistant", content=full_response,
                    model=payload.model or settings.ai_model,
                )
                session.add(assistant)
                conv = session.query(Conversation).filter_by(id=conversation_id).first()
                if conv:
                    conv.updated_at = datetime.now(timezone.utc)
                session.commit()
            yield f"event: done\ndata: {json.dumps({'ok': True})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/api/models")
def list_models():
    return {"provider": settings.ai_provider, "models": [{"id": settings.ai_model, "label": settings.ai_model, "default": True}]}
