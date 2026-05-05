"""게시판 리포지토리 — 글/이미지/댓글/좋아요.

목록 조회는 N+1 방지를 위해 좋아요 수·댓글 수·my_liked를 한 쿼리로 join+aggregate.
"""
from db.database import get_connection


def _post_row_to_dict(row, current_user_id: int) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "author_name": row["author_name"],
        "saved_recipe_id": row["saved_recipe_id"],
        "saved_recipe_name": row["saved_recipe_name"],
        "content": row["content"],
        "rating": row["rating"],
        "comments_enabled": bool(row["comments_enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "like_count": row["like_count"],
        "comment_count": row["comment_count"],
        "my_liked": bool(row["my_liked"]),
        "is_mine": row["user_id"] == current_user_id,
    }


# ---------- Posts ----------

def list_posts(current_user_id: int, offset: int = 0, limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            p.id, p.user_id, p.saved_recipe_id, p.content, p.rating,
            p.comments_enabled, p.created_at, p.updated_at,
            u.display_name AS author_name,
            sr.name AS saved_recipe_name,
            (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id) AS like_count,
            (SELECT COUNT(*) FROM post_comments WHERE post_id = p.id) AS comment_count,
            (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id AND user_id = ?) AS my_liked
        FROM posts p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN saved_recipes sr ON sr.id = p.saved_recipe_id
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
        """,
        (current_user_id, limit, offset),
    ).fetchall()
    posts = [_post_row_to_dict(r, current_user_id) for r in rows]

    # 이미지 일괄 로드 — 글당 0~3개라 N+1 큰 영향 없지만 한 쿼리로
    if posts:
        ids = [p["id"] for p in posts]
        placeholders = ",".join("?" * len(ids))
        img_rows = conn.execute(
            f"""SELECT post_id, storage_path FROM post_images
                WHERE post_id IN ({placeholders})
                ORDER BY post_id, sort_order""",
            ids,
        ).fetchall()
        by_post: dict[int, list[str]] = {pid: [] for pid in ids}
        for r in img_rows:
            by_post[r["post_id"]].append(r["storage_path"])
        for p in posts:
            p["images"] = by_post.get(p["id"], [])
    conn.close()
    return posts


def get_post(post_id: int, current_user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            p.id, p.user_id, p.saved_recipe_id, p.content, p.rating,
            p.comments_enabled, p.created_at, p.updated_at,
            u.display_name AS author_name,
            sr.name AS saved_recipe_name,
            (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id) AS like_count,
            (SELECT COUNT(*) FROM post_comments WHERE post_id = p.id) AS comment_count,
            (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id AND user_id = ?) AS my_liked
        FROM posts p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN saved_recipes sr ON sr.id = p.saved_recipe_id
        WHERE p.id = ?
        """,
        (current_user_id, post_id),
    ).fetchone()
    if row is None:
        conn.close()
        return None
    post = _post_row_to_dict(row, current_user_id)
    img_rows = conn.execute(
        "SELECT storage_path FROM post_images WHERE post_id = ? ORDER BY sort_order",
        (post_id,),
    ).fetchall()
    post["images"] = [r["storage_path"] for r in img_rows]
    conn.close()
    return post


def create_post(
    user_id: int,
    content: str,
    rating: int,
    comments_enabled: bool,
    saved_recipe_id: int | None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO posts (user_id, saved_recipe_id, content, rating, comments_enabled)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, saved_recipe_id, content, rating, 1 if comments_enabled else 0),
    )
    post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return post_id


def add_post_image(post_id: int, storage_path: str, sort_order: int) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO post_images (post_id, storage_path, sort_order) VALUES (?, ?, ?)",
        (post_id, storage_path, sort_order),
    )
    conn.commit()
    conn.close()


def update_post(
    post_id: int,
    user_id: int,
    content: str | None = None,
    comments_enabled: bool | None = None,
) -> bool:
    """본인 게시글만 수정. 수정된 행이 있으면 True."""
    fields, values = [], []
    if content is not None:
        fields.append("content = ?")
        values.append(content)
    if comments_enabled is not None:
        fields.append("comments_enabled = ?")
        values.append(1 if comments_enabled else 0)
    if not fields:
        return False
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.extend([post_id, user_id])
    conn = get_connection()
    cur = conn.execute(
        f"UPDATE posts SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
        values,
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def delete_post(post_id: int, user_id: int) -> list[str]:
    """본인 게시글 삭제. cascade로 이미지/댓글/좋아요 모두 사라짐.
    삭제된 이미지 storage_path 리스트 반환 — 호출자가 디스크 파일 정리."""
    conn = get_connection()
    img_rows = conn.execute(
        """SELECT storage_path FROM post_images
           WHERE post_id = ? AND post_id IN (SELECT id FROM posts WHERE id = ? AND user_id = ?)""",
        (post_id, post_id, user_id),
    ).fetchall()
    paths = [r["storage_path"] for r in img_rows]
    conn.execute("DELETE FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id))
    conn.commit()
    conn.close()
    return paths


def get_user_image_paths(user_id: int) -> list[str]:
    """해당 사용자가 작성한 모든 게시글의 이미지 storage_path. 사용자 삭제 직전에 호출해
    cascade로 DB 행이 사라지기 전에 디스크 파일 경로를 확보."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT pi.storage_path
           FROM post_images pi
           JOIN posts p ON p.id = pi.post_id
           WHERE p.user_id = ?""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [r["storage_path"] for r in rows]


def get_post_owner(post_id: int) -> int | None:
    conn = get_connection()
    row = conn.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return row["user_id"] if row else None


def is_comments_enabled(post_id: int) -> bool | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT comments_enabled FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return bool(row["comments_enabled"])


# ---------- Likes ----------

def toggle_like(post_id: int, user_id: int) -> tuple[bool, int]:
    """좋아요 토글. (now_liked, total_count) 반환."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    ).fetchone()
    if existing:
        conn.execute(
            "DELETE FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id)
        )
        now_liked = False
    else:
        conn.execute(
            "INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id)
        )
        now_liked = True
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM post_likes WHERE post_id = ?", (post_id,)
    ).fetchone()["c"]
    conn.commit()
    conn.close()
    return now_liked, count


# ---------- Comments ----------

def list_comments(post_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.id, c.post_id, c.user_id, c.content, c.created_at,
                  u.display_name AS author_name
           FROM post_comments c
           JOIN users u ON u.id = c.user_id
           WHERE c.post_id = ?
           ORDER BY c.created_at ASC""",
        (post_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "post_id": r["post_id"],
            "user_id": r["user_id"],
            "author_name": r["author_name"],
            "content": r["content"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def create_comment(post_id: int, user_id: int, content: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO post_comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (post_id, user_id, content),
    )
    comment_id = cur.lastrowid
    conn.commit()
    conn.close()
    return comment_id


def get_comment_owner(comment_id: int) -> int | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id FROM post_comments WHERE id = ?", (comment_id,)
    ).fetchone()
    conn.close()
    return row["user_id"] if row else None


def delete_comment(comment_id: int, user_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute(
        "DELETE FROM post_comments WHERE id = ? AND user_id = ?",
        (comment_id, user_id),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0
