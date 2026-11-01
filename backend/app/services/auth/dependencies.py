from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuthSession
from app.services.auth.security import get_session_by_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthSession | None:
    if credentials is None:
        return None

    auth_session = get_session_by_token(db, credentials.credentials)

    if auth_session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    return auth_session


def get_current_session(
    auth_session: AuthSession | None = Depends(get_optional_session),
) -> AuthSession:
    if auth_session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return auth_session
