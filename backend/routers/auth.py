"""인증 엔드포인트: 이메일+비밀번호 가입/로그인, Google ID 토큰 교환, 프로필 조회·수정."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.auth import (
    CurrentUser,
    hash_password,
    issue_token,
    verify_google_id_token,
    verify_password,
)
from db.models import User
from db.users import (
    CannotDeleteLegacyUser,
    EmailAlreadyExists,
    create_user_email,
    create_user_google,
    delete_user,
    get_user_by_email,
    get_user_by_google_sub,
    update_display_name,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Schemas ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=40)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str | None
    auth_provider: str  # "email" | "google"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DisplayNameUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


def _user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        auth_provider="google" if user.google_sub else "email",
    )


# ---------- Endpoints ----------

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    """이메일+비밀번호 회원가입. 같은 이메일이 이미 있으면 409."""
    try:
        user = create_user_email(
            email=str(req.email),
            password_hash=hash_password(req.password),
            display_name=req.display_name.strip(),
        )
    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="email_already_exists")
    return TokenResponse(access_token=issue_token(user.id), user=_user_to_out(user))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """이메일+비밀번호 로그인."""
    user = get_user_by_email(str(req.email))
    if user is None or user.password_hash is None:
        # 이메일 미존재 또는 Google 가입자가 비번 로그인 시도
        raise HTTPException(status_code=401, detail="invalid_credentials")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return TokenResponse(access_token=issue_token(user.id), user=_user_to_out(user))


@router.post("/google", response_model=TokenResponse)
def google_login(req: GoogleLoginRequest):
    """Google ID 토큰 → 자체 JWT 교환. 신규 사용자는 즉시 가입됩니다."""
    info = verify_google_id_token(req.id_token)
    google_sub = info["sub"]
    email = info["email"]
    name = info.get("name") or info.get("given_name")

    user = get_user_by_google_sub(google_sub)
    if user is None:
        try:
            user = create_user_google(email=email, google_sub=google_sub, display_name=name)
        except EmailAlreadyExists:
            # 같은 이메일이 이미 이메일+PW로 가입되어 있음 — 정책 A: 차단
            raise HTTPException(
                status_code=409,
                detail="email_already_exists_with_password_login",
            )
    return TokenResponse(access_token=issue_token(user.id), user=_user_to_out(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return _user_to_out(user)


@router.patch("/me", response_model=UserOut)
def patch_me(body: DisplayNameUpdate, user: CurrentUser):
    update_display_name(user.id, body.display_name.strip())
    user.display_name = body.display_name.strip()
    return _user_to_out(user)


@router.delete("/me", status_code=204)
def delete_me(user: CurrentUser):
    """계정 + 모든 데이터 영구 삭제 (Play Store 정책 필수).

    cascade 규칙으로 ingredients/user_profile/saved_recipes/shopping_list/daily_recipes
    가 자동으로 함께 삭제됩니다. 클라이언트는 응답 후 토큰/유저 캐시를 비워야 합니다.
    """
    try:
        delete_user(user.id)
    except CannotDeleteLegacyUser:
        # 운영 중 발생하면 안 되는 케이스 — 로그인 발급 자체가 LEGACY_USER_ID에 대해선 일어나지 않음.
        raise HTTPException(status_code=403, detail="cannot_delete_system_account")
    return None
