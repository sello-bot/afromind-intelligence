import base64
import hashlib
import hmac
import secrets
import uuid

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import AuthSession


PASSWORD_ITERATIONS = 310000
GUEST_SESSION_DAYS = 7
USER_SESSION_DAYS = 30


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters.")

    salt = secrets.token_bytes(16)

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_key = base64.b64encode(derived_key).decode("ascii")

    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${encoded_salt}${encoded_key}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_key = stored_hash.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(encoded_salt)
        expected_key = base64.b64decode(encoded_key)

        actual_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(actual_key, expected_key)

    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    db: Session,
    user_id: str | None = None,
) -> tuple[AuthSession, str]:

    token = secrets.token_urlsafe(32)

    session_id = str(uuid.uuid4())
    owner_id = user_id or str(uuid.uuid4())

    lifetime = (
        USER_SESSION_DAYS if user_id else GUEST_SESSION_DAYS
    )

    auth_session = AuthSession(
        id=session_id,
        token_hash=hash_token(token),
        owner_id=owner_id,
        user_id=user_id,
        questions_used=0,
        questions_reserved=0,
        expires_at=datetime.now(timezone.utc) + timedelta(days=lifetime),
    )

    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)

    return auth_session, token


def get_session_by_token(
    db: Session,
    token: str,
) -> AuthSession | None:

    auth_session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == hash_token(token))
        .first()
    )

    if not auth_session:
        return None

    expires_at = auth_session.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        db.delete(auth_session)
        db.commit()
        return None

    return auth_session
