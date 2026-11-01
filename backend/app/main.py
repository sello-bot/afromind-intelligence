import json
import uuid

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import update, inspect, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import Base, SessionLocal, engine, get_db
from app.models import AuthSession, Conversation, Message
from app.schemas import ChatRequest, ConversationOut, MessageOut

from app.services.auth.routes import router as auth_router
from app.services.auth.dependencies import get_current_session
from app.services.ai.router import model_router
from app.services.files.processor import analyse_file, MAX_FILE_BYTES
from app.services.ai.instructions import build_system_instruction


GUEST_QUESTION_LIMIT = 3

Base.metadata.create_all(bind=engine)

# Safely add the name column to existing user databases.
# Existing accounts are preserved and receive a display fallback.
user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
if "name" not in user_columns:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(120)"))

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Afromind Intelligence API — powered by KGOLE AI",
)

app.include_router(auth_router)

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
        "assistant": "KGOLE AI",
    }


@app.get("/api/conversations", response_model=list[ConversationOut])
def list_conversations(
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return (
        db.query(Conversation)
        .filter(Conversation.owner_id == auth_session.owner_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@app.get(
    "/api/conversations/{conversation_id}",
    response_model=list[MessageOut],
)
def get_messages(
    conversation_id: str,
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    conversation = db.query(Conversation).filter_by(
        id=conversation_id,
        owner_id=auth_session.owner_id,
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation.messages


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    conversation = db.query(Conversation).filter_by(
        id=conversation_id,
        owner_id=auth_session.owner_id,
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()

    return {"deleted": True}


@app.post("/api/files/analyze")
async def analyze_uploaded_file(
    file: UploadFile = File(...),
    auth_session: AuthSession = Depends(get_current_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    content = await file.read(MAX_FILE_BYTES + 1)
    await file.close()

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Files must be 10 MB or smaller.",
        )

    try:
        return await analyse_file(file.filename, content)

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The file could not be processed.",
        )


@app.post("/api/chat")
async def chat(
    payload: ChatRequest,
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    is_guest = auth_session.user_id is None

    # Atomically reserve one guest question.
    if is_guest:
        reservation = db.execute(
            update(AuthSession)
            .where(
                AuthSession.id == auth_session.id,
                (
                    AuthSession.questions_used
                    + AuthSession.questions_reserved
                ) < GUEST_QUESTION_LIMIT,
            )
            .values(
                questions_reserved=AuthSession.questions_reserved + 1
            )
        )

        db.commit()

        if reservation.rowcount != 1:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "GUEST_LIMIT_REACHED",
                    "message": (
                        "You've used your three free questions. "
                        "Create an account or log in to continue."
                    ),
                },
            )

    # Find or create the visitor's conversation.
    if payload.conversation_id:
        conversation = db.query(Conversation).filter_by(
            id=payload.conversation_id,
            owner_id=auth_session.owner_id,
        ).first()

        if not conversation:
            if is_guest:
                with SessionLocal() as session:
                    session.execute(
                        update(AuthSession)
                        .where(
                            AuthSession.id == auth_session.id,
                            AuthSession.questions_reserved > 0,
                        )
                        .values(
                            questions_reserved=(
                                AuthSession.questions_reserved - 1
                            )
                        )
                    )
                    session.commit()

            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

    else:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            owner_id=auth_session.owner_id,
            title=payload.message[:60].strip() or "New conversation",
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    conversation_id = conversation.id

    user_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=payload.message,
    )

    db.add(user_message)
    db.commit()

    prior_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    history = [
        {
            "role": "system",
            "content": build_system_instruction(),
        }
    ]

    history.extend(
        [
            {"role": message.role, "content": message.content}
            for message in prior_messages
        ]
    )

    session_id = auth_session.id
    selected_model = payload.model or settings.ai_model

    async def event_stream():
        full_response = ""
        completed = False

        try:
            provider = model_router.get_provider(settings.ai_provider)

            yield (
                f"event: meta\ndata: {json.dumps({
                    'conversation_id': conversation_id,
                    'model': selected_model,
                })}\n\n"
            )

            async for token in provider.stream_chat(
                history,
                payload.model,
            ):
                full_response += token

                yield f"data: {json.dumps({'token': token})}\n\n"

            if not full_response.strip():
                raise RuntimeError("KGOLE AI returned an empty response.")

            with SessionLocal() as session:
                assistant = Message(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    model=selected_model,
                )

                session.add(assistant)

                current_conversation = session.query(
                    Conversation
                ).filter_by(id=conversation_id).first()

                if current_conversation:
                    current_conversation.updated_at = datetime.now(
                        timezone.utc
                    )

                # Consume the reserved question only after success.
                if is_guest:
                    result = session.execute(
                        update(AuthSession)
                        .where(
                            AuthSession.id == session_id,
                            AuthSession.questions_reserved > 0,
                        )
                        .values(
                            questions_used=AuthSession.questions_used + 1,
                            questions_reserved=(
                                AuthSession.questions_reserved - 1
                            ),
                        )
                    )

                    if result.rowcount != 1:
                        raise RuntimeError(
                            "Could not finalize the guest question."
                        )

                session.commit()

            completed = True

            remaining = None

            if is_guest:
                with SessionLocal() as session:
                    current = session.query(AuthSession).filter_by(
                        id=session_id
                    ).first()

                    if current:
                        remaining = max(
                            0,
                            GUEST_QUESTION_LIMIT
                            - current.questions_used
                            - current.questions_reserved,
                        )

            yield (
                f"event: done\ndata: {json.dumps({
                    'ok': True,
                    'questions_remaining': remaining,
                })}\n\n"
            )

        except Exception as exc:
            yield (
                f"event: error\ndata: {json.dumps({
                    'error': str(exc),
                })}\n\n"
            )

        finally:
            # Release the reservation on failure or disconnection.
            if is_guest and not completed:
                with SessionLocal() as session:
                    session.execute(
                        update(AuthSession)
                        .where(
                            AuthSession.id == session_id,
                            AuthSession.questions_reserved > 0,
                        )
                        .values(
                            questions_reserved=(
                                AuthSession.questions_reserved - 1
                            )
                        )
                    )

                    session.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/models")
def list_models():
    return {
        "provider": settings.ai_provider,
        "models": [
            {
                "id": settings.ai_model,
                "label": settings.ai_model,
                "default": True,
            }
        ],
    }
