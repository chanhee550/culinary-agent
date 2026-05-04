"""게시판 — 글 CRUD, 좋아요, 댓글. 작성/수정 시 모더레이션 자동 적용.

차단 시: 422 Unprocessable Entity + payload {detail, warning_count, warning_limit, account_deleted}.
3회 누적 → users.increment_warning이 계정을 즉시 삭제하고 account_deleted=True.
"""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.auth import CurrentUser
from db.posts import (
    add_post_image,
    create_comment,
    create_post,
    delete_comment,
    delete_post,
    get_comment_owner,
    get_post,
    get_post_owner,
    get_user_image_paths,
    is_comments_enabled,
    list_comments,
    list_posts,
    toggle_like,
    update_post,
)
from db.users import WARNING_LIMIT, delete_user, get_warning_count, increment_warning
from services.moderation import check_images, check_text

logger = logging.getLogger(__name__)
router = APIRouter(tags=["posts"])

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "data" / "uploads" / "posts"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


# ---------- Schemas ----------

class PostOut(BaseModel):
    id: int
    user_id: int
    author_name: str | None
    saved_recipe_id: int | None
    saved_recipe_name: str | None
    content: str
    rating: int
    comments_enabled: bool
    created_at: str
    updated_at: str
    like_count: int
    comment_count: int
    my_liked: bool
    is_mine: bool
    images: list[str] = []


class PostUpdate(BaseModel):
    content: str | None = None
    comments_enabled: bool | None = None


class CommentOut(BaseModel):
    id: int
    post_id: int
    user_id: int
    author_name: str | None
    content: str
    created_at: str


class CommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class LikeToggleOut(BaseModel):
    liked: bool
    like_count: int


class ModerationBlockedDetail(BaseModel):
    """차단 시 422로 반환되는 payload."""
    detail: str  # "blocked"
    reason: str  # 사용자에게 보여줄 사유
    warning_count: int
    warning_limit: int
    account_deleted: bool


# ---------- Helpers ----------

def _moderation_blocked(user_id: int, reason: str) -> HTTPException:
    """경고 +1 + (3회 누적 시 계정 삭제 + 디스크 이미지 정리) 후 422 HTTPException."""
    new_count, should_delete = increment_warning(user_id)
    if should_delete:
        # 디스크 경로를 cascade 전에 확보, 사용자 삭제 후 디스크 파일 정리
        paths = get_user_image_paths(user_id)
        delete_user(user_id)
        delete_image_files_from_disk(paths)
    payload = {
        "detail": "blocked",
        "reason": reason,
        "warning_count": new_count,
        "warning_limit": WARNING_LIMIT,
        "account_deleted": should_delete,
    }
    logger.warning(
        "moderation block user=%s reason=%s warnings=%s/%s deleted=%s",
        user_id, reason, new_count, WARNING_LIMIT, should_delete,
    )
    return HTTPException(status_code=422, detail=payload)


def _validate_uploads(files: list[UploadFile]) -> list[tuple[bytes, str, str]]:
    """업로드 검증 + 바이트 읽기. (data, content_type, ext) 리스트.
    개수/크기/MIME 위반 시 400."""
    if len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"이미지는 최대 {MAX_IMAGES}장까지 업로드 가능해요.")
    out: list[tuple[bytes, str, str]] = []
    for f in files:
        ctype = (f.content_type or "").lower()
        if ctype not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 이미지 형식입니다: {ctype}")
        data = f.file.read()
        if not data:
            continue
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="이미지 1장당 5MB까지만 업로드 가능해요.")
        ext = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}[ctype]
        out.append((data, ctype, ext))
    return out


def _save_image(post_id: int, idx: int, data: bytes, ext: str) -> str:
    """이미지를 디스크에 저장하고 공개 URL 경로 반환."""
    dir_ = UPLOAD_ROOT / str(post_id)
    dir_.mkdir(parents=True, exist_ok=True)
    name = f"{idx}_{uuid.uuid4().hex[:8]}.{ext}"
    path = dir_ / name
    path.write_bytes(data)
    # 클라이언트에서 그대로 <img src=...>로 쓸 수 있는 상대 URL
    return f"/uploads/posts/{post_id}/{name}"


def delete_image_files_from_disk(paths: list[str]) -> None:
    """저장된 이미지 파일을 디스크에서 정리. 폴더가 비면 폴더도 삭제.
    routers/auth.py 의 계정 삭제 경로에서도 import해서 사용."""
    dirs: set[Path] = set()
    for url_path in paths:
        # url_path는 /uploads/posts/{pid}/{file} 형태
        rel = url_path.lstrip("/")
        full = UPLOAD_ROOT.parents[1] / rel  # data/uploads/posts/{pid}/{file}
        try:
            if full.exists():
                full.unlink()
                dirs.add(full.parent)
        except OSError as e:
            logger.warning("이미지 삭제 실패 %s: %s", full, e)
    for d in dirs:
        try:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass


# ---------- Posts ----------

@router.get("/posts", response_model=list[PostOut])
def list_posts_endpoint(
    user: CurrentUser,
    offset: int = 0,
    limit: int = 20,
):
    limit = min(max(limit, 1), 50)
    offset = max(offset, 0)
    return list_posts(current_user_id=user.id, offset=offset, limit=limit)


@router.get("/posts/{post_id}", response_model=PostOut)
def get_post_endpoint(post_id: int, user: CurrentUser):
    post = get_post(post_id, current_user_id=user.id)
    if post is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없어요.")
    return post


@router.post("/posts", response_model=PostOut)
def create_post_endpoint(
    user: CurrentUser,
    content: str = Form(..., min_length=1, max_length=2000),
    rating: int = Form(..., ge=1, le=5),
    comments_enabled: bool = Form(True),
    saved_recipe_id: int | None = Form(None),
    images: list[UploadFile] = File(default=[]),
):
    """게시글 작성. 텍스트+이미지 모더레이션을 거친 뒤 저장."""
    # 1) 텍스트 모더레이션
    text_check = check_text(content)
    if text_check.blocked:
        raise _moderation_blocked(user.id, text_check.reason)

    # 2) 업로드 검증 + 바이트 로드
    upload_data = _validate_uploads(images)

    # 3) 이미지 모더레이션
    img_check = check_images([(d, ct) for d, ct, _ in upload_data])
    if img_check.blocked:
        raise _moderation_blocked(user.id, img_check.reason)

    # 4) 글 + 이미지 저장
    post_id = create_post(
        user_id=user.id,
        content=content.strip(),
        rating=rating,
        comments_enabled=comments_enabled,
        saved_recipe_id=saved_recipe_id,
    )
    for idx, (data, _ctype, ext) in enumerate(upload_data):
        url_path = _save_image(post_id, idx, data, ext)
        add_post_image(post_id, url_path, idx)

    return get_post(post_id, current_user_id=user.id)


@router.patch("/posts/{post_id}", response_model=PostOut)
def update_post_endpoint(post_id: int, body: PostUpdate, user: CurrentUser):
    owner = get_post_owner(post_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없어요.")
    if owner != user.id:
        raise HTTPException(status_code=403, detail="본인 글만 수정할 수 있어요.")

    if body.content is not None:
        text_check = check_text(body.content)
        if text_check.blocked:
            raise _moderation_blocked(user.id, text_check.reason)

    update_post(
        post_id,
        user_id=user.id,
        content=body.content.strip() if body.content is not None else None,
        comments_enabled=body.comments_enabled,
    )
    return get_post(post_id, current_user_id=user.id)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post_endpoint(post_id: int, user: CurrentUser):
    owner = get_post_owner(post_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없어요.")
    if owner != user.id:
        raise HTTPException(status_code=403, detail="본인 글만 삭제할 수 있어요.")
    paths = delete_post(post_id, user_id=user.id)
    delete_image_files_from_disk(paths)
    return None


# ---------- Likes ----------

@router.post("/posts/{post_id}/like", response_model=LikeToggleOut)
def toggle_like_endpoint(post_id: int, user: CurrentUser):
    if get_post_owner(post_id) is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없어요.")
    liked, count = toggle_like(post_id, user_id=user.id)
    return LikeToggleOut(liked=liked, like_count=count)


# ---------- Comments ----------

@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
def list_comments_endpoint(post_id: int, user: CurrentUser):
    if get_post_owner(post_id) is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없어요.")
    return list_comments(post_id)


@router.post("/posts/{post_id}/comments", response_model=CommentOut)
def create_comment_endpoint(post_id: int, body: CommentIn, user: CurrentUser):
    enabled = is_comments_enabled(post_id)
    if enabled is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없어요.")
    if not enabled:
        raise HTTPException(status_code=403, detail="이 글은 댓글이 비활성화되어 있어요.")

    text_check = check_text(body.content)
    if text_check.blocked:
        raise _moderation_blocked(user.id, text_check.reason)

    cid = create_comment(post_id, user_id=user.id, content=body.content.strip())
    # 갓 만든 행을 다시 가져오기
    items = list_comments(post_id)
    for c in items:
        if c["id"] == cid:
            return c
    # 정상 케이스에서 도달하지 않음
    raise HTTPException(status_code=500, detail="댓글 생성 후 조회 실패")


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment_endpoint(comment_id: int, user: CurrentUser):
    owner = get_comment_owner(comment_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없어요.")
    if owner != user.id:
        raise HTTPException(status_code=403, detail="본인 댓글만 삭제할 수 있어요.")
    delete_comment(comment_id, user_id=user.id)
    return None


# ---------- Profile (warnings 노출) ----------

@router.get("/me/warnings")
def my_warnings(user: CurrentUser):
    return {
        "warning_count": get_warning_count(user.id),
        "warning_limit": WARNING_LIMIT,
    }
