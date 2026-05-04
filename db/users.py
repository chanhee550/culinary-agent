"""사용자 인증/프로필 리포지토리.

이메일+비밀번호 또는 Google OAuth 양쪽 모두를 한 테이블에서 처리합니다.
- 이메일 가입자: password_hash 채움, google_sub NULL
- Google 가입자: google_sub 채움, password_hash NULL

같은 이메일이 양쪽 방식으로 가입을 시도하면 EmailAlreadyExists를 던집니다 (계정 연결 정책 A).
"""
from db.database import get_connection, LEGACY_USER_ID
from db.models import User


class EmailAlreadyExists(Exception):
    """이미 다른 인증 방식으로 가입된 이메일입니다."""


def _row_to_user(row) -> User | None:
    if row is None:
        return None
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        google_sub=row["google_sub"],
        display_name=row["display_name"],
        created_at=row["created_at"],
    )


def get_user_by_id(user_id: int) -> User | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _row_to_user(row)


def get_user_by_email(email: str) -> User | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    conn.close()
    return _row_to_user(row)


def get_user_by_google_sub(google_sub: str) -> User | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
    conn.close()
    return _row_to_user(row)


def create_user_email(email: str, password_hash: str, display_name: str) -> User:
    """이메일+비밀번호 가입. 이미 같은 이메일이 있으면 EmailAlreadyExists."""
    email = email.lower()
    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        raise EmailAlreadyExists(email)
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
        (email, password_hash, display_name),
    )
    user_id = cur.lastrowid
    conn.execute("INSERT OR IGNORE INTO user_profile (user_id) VALUES (?)", (user_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _row_to_user(row)


def create_user_google(email: str, google_sub: str, display_name: str | None) -> User:
    """Google 가입. 같은 이메일이 이메일+PW로 이미 있으면 EmailAlreadyExists."""
    email = email.lower()
    conn = get_connection()
    existing = conn.execute("SELECT id, google_sub FROM users WHERE email = ?", (email,)).fetchone()
    if existing and existing["google_sub"] != google_sub:
        conn.close()
        raise EmailAlreadyExists(email)
    cur = conn.execute(
        "INSERT INTO users (email, google_sub, display_name) VALUES (?, ?, ?)",
        (email, google_sub, display_name),
    )
    user_id = cur.lastrowid
    conn.execute("INSERT OR IGNORE INTO user_profile (user_id) VALUES (?)", (user_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _row_to_user(row)


def update_display_name(user_id: int, display_name: str):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id)
    )
    conn.commit()
    conn.close()


class CannotDeleteLegacyUser(Exception):
    """LEGACY_USER_ID(1)는 Streamlit 폴백/시드용 더미 계정이라 삭제하지 않습니다."""


def delete_user(user_id: int) -> None:
    """사용자 + 소유 데이터 전부 삭제 (Play Store 계정 삭제 정책 충족).

    모든 도메인 테이블에 user_id ON DELETE CASCADE가 걸려있고
    get_connection()이 PRAGMA foreign_keys=ON을 켜기 때문에
    users 행만 지우면 ingredients/profile/saved/shopping/daily 모두 함께 사라집니다.
    """
    if user_id == LEGACY_USER_ID:
        raise CannotDeleteLegacyUser()
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
