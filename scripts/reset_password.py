"""로컬 DB의 비밀번호 리셋 CLI.

사용법:
    python -m scripts.reset_password <email> <new_password>

    # 사용자 목록만 보고 싶을 때
    python -m scripts.reset_password --list

이메일+비번 가입자만 대상입니다. Google 가입자는 비번이 없어서 거부됩니다.
"""
import sys

from backend.auth import hash_password
from db.database import get_connection
from db.users import get_user_by_email


def list_users() -> None:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, email, display_name, "
        "CASE WHEN google_sub IS NOT NULL THEN 'google' ELSE 'email' END AS provider "
        "FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    if not rows:
        print("(no users)")
        return
    print(f"{'id':>3}  {'provider':<8}  {'email':<32}  display_name")
    print("-" * 70)
    for r in rows:
        print(f"{r['id']:>3}  {r['provider']:<8}  {r['email']:<32}  {r['display_name'] or ''}")


def reset(email: str, new_password: str) -> None:
    if len(new_password) < 8:
        sys.exit("error: password must be at least 8 characters")
    user = get_user_by_email(email)
    if user is None:
        sys.exit(f"error: no user with email {email!r}")
    if user.password_hash is None:
        sys.exit(f"error: {email!r} is a Google-auth account (no password to reset)")
    new_hash = hash_password(new_password)
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user.id))
    conn.commit()
    conn.close()
    print(f"ok: password reset for {email} (id={user.id})")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--list":
        list_users()
        return
    if len(args) != 2:
        sys.exit("usage: python -m scripts.reset_password <email> <new_password>")
    reset(args[0], args[1])


if __name__ == "__main__":
    main()
