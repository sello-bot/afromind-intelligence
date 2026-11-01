import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuthSession, Conversation, User
from app.services.auth.dependencies import (
    get_current_session,
    get_optional_session,
)
from app.services.auth.schemas import LoginRequest, RegisterRequest
from app.services.auth.security import (
    GUEST_SESSION_DAYS,
    USER_SESSION_DAYS,
    create_session,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

GUEST_QUESTION_LIMIT = 3


def session_response(auth_session, token=None):
    is_authenticated = auth_session.user_id is not None

    return {
        "access_token": token,
        "token_type": "bearer",
        "session_type": "user" if is_authenticated else "guest",
        "authenticated": is_authenticated,
        "questions_used": auth_session.questions_used,
        "questions_remaining": (
            None
            if is_authenticated
            else max(
                0,
                GUEST_QUESTION_LIMIT
                - auth_session.questions_used
                - auth_session.questions_reserved,
            )
        ),
        "user": (
            {
                "id": auth_session.user.id,
                "name": auth_session.user.name or auth_session.user.email.split("@")[0],
                "email": auth_session.user.email,
            }
            if is_authenticated and auth_session.user
            else None
        ),
    }


def migrate_guest_conversations(db, guest_session, user):
    if not guest_session or guest_session.user_id is not None:
        return

    db.query(Conversation).filter(
        Conversation.owner_id == guest_session.owner_id
    ).update(
        {Conversation.owner_id: user.id},
        synchronize_session=False,
    )

    db.delete(guest_session)
    db.commit()


@router.post("/guest")
def create_guest(
    db: Session = Depends(get_db),
):
    auth_session, token = create_session(db)

    return session_response(auth_session, token)


@router.post("/register")
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    guest_session: AuthSession | None = Depends(get_optional_session),
):
    name = payload.name.strip()
    email = payload.email.strip().lower()

    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Enter your full name.")

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    existing_user = db.query(User).filter(
        func.lower(User.email) == email
    ).first()

    if existing_user:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    try:
        user = User(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    auth_session, token = create_session(db, user_id=user.id)

    migrate_guest_conversations(db, guest_session, user)

    return session_response(auth_session, token)


@router.post("/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    guest_session: AuthSession | None = Depends(get_optional_session),
):
    email = payload.email.strip().lower()

    user = db.query(User).filter(
        func.lower(User.email) == email
    ).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    auth_session, token = create_session(db, user_id=user.id)

    migrate_guest_conversations(db, guest_session, user)

    return session_response(auth_session, token)


@router.get("/me")
def get_me(
    auth_session: AuthSession = Depends(get_current_session),
):
    return session_response(auth_session)


@router.post("/logout")
def logout(
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    db.delete(auth_session)
    db.commit()

    return {"logged_out": True}
