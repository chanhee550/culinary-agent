"""인증 유틸리티 — 비밀번호 해시, JWT 발급/검증, Google ID 토큰 검증, FastAPI 의존성.

흐름:
- 이메일+비번: register/login에서 password_hash 생성·검증 → 자체 JWT 발급
- Google: GIS가 발급한 ID 토큰을 백엔드에서 google.oauth2.id_token으로 검증 → 자체 JWT 발급
- 이후 모든 요청은 Authorization: Bearer <자체 JWT> 헤더로 인증

자체 JWT의 sub 클레임에 user_id를 string으로 담습니다.
"""
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from jose import jwt, JWTError

from db.models import User
from db.users import get_user_by_id

# bcrypt에는 72바이트 제한이 있어, 긴 비밀번호 또는 멀티바이트 문자(한글)에서
# 잘림이 발생합니다. 사전 SHA-256으로 고정 32바이트로 줄여서 해결합니다.
# (이 패턴은 dropbox/Stack Overflow에서 광범위하게 권장됨)
_BCRYPT_ROUNDS = 12


def _to_72(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET 환경변수가 설정되지 않았습니다. .env에 추가하세요."
        )
    return secret


def _jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def _jwt_expire_minutes() -> int:
    return int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 기본 7일


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_to_72(plain), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_72(plain), hashed.encode())
    except (ValueError, TypeError):
        return False


def issue_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=_jwt_expire_minutes())).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_token(token: str) -> int:
    """JWT를 검증하고 user_id(int)를 반환. 실패 시 401."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid_token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token: no sub",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token: bad sub",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_google_id_token(id_token_str: str) -> dict:
    """Google ID 토큰을 검증해 payload({email, sub, name, ...})를 반환합니다.

    GOOGLE_CLIENT_ID 환경변수와 audience가 일치해야 합니다 (Google이 발급할 때
    이 client_id를 audience로 박아넣음).
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="server_misconfigured: GOOGLE_CLIENT_ID 미설정",
        )

    # google-auth는 lazy-import — 라이브러리가 설치 안 된 환경에서도 다른 코드는 import 가능하게.
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as g_id_token
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="server_misconfigured: google-auth 미설치 (pip install google-auth)",
        )

    try:
        info = g_id_token.verify_oauth2_token(
            id_token_str, g_requests.Request(), client_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid_google_token: {e}",
        )

    if info.get("aud") != client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_google_token: audience mismatch",
        )

    if not info.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="email_not_verified",
        )

    return info


# ===== FastAPI 의존성 =====

def get_current_user(authorization: str | None = Header(default=None)) -> User:
    """Authorization: Bearer <token> 헤더에서 user를 꺼냅니다."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_bearer_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_token(token)
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user_not_found",
        )
    return user


# 라우터에서 `def endpoint(user: CurrentUser):` 한 줄로 사용.
CurrentUser = Annotated[User, Depends(get_current_user)]
