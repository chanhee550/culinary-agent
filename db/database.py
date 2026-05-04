import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "culinary.db"

LEGACY_USER_ID = 1


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def init_db():
    """스키마 초기화 + 레거시 마이그레이션. idempotent.

    실행 순서가 중요합니다:
    1) users 테이블 생성 + 레거시 사용자 시드
    2) 기존 테이블이 있다면 멀티사용자 스키마로 변환 (user_id 컬럼 추가, 인덱스 재구성)
    3) 그 외 테이블이 없다면 새 스키마로 생성
    4) 새 사용자용 기본 프로필 시드
    """
    conn = get_connection()

    # 1) users — 인증 주체
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            google_sub TEXT UNIQUE,
            display_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 레거시 데이터를 귀속시킬 더미 사용자 — 인증 엔드포인트는 이 계정을 발급하지 않음.
    conn.execute("""
        INSERT OR IGNORE INTO users (id, email, display_name)
        VALUES (?, 'legacy@local.invalid', '레거시 사용자')
    """, (LEGACY_USER_ID,))

    # 2) 레거시 스키마가 있다면 멀티사용자 스키마로 변환
    _migrate_legacy_schema(conn)

    # 3) 신규 환경에서 테이블이 아직 없으면 새 스키마로 생성
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            category TEXT DEFAULT '기타',
            quantity TEXT,
            expiry_date TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'manual',
            UNIQUE(user_id, name)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            skill_level TEXT DEFAULT '초보',
            cuisine_preference TEXT DEFAULT '',
            taste_preference TEXT DEFAULT '',
            allergies TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            ingredients TEXT,
            missing TEXT,
            instructions TEXT,
            difficulty TEXT,
            time TEXT,
            substitutions TEXT,
            rating INTEGER,
            saved_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            quantity TEXT,
            category TEXT DEFAULT '기타',
            checked INTEGER DEFAULT 0,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_recipes (
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            recipes_json TEXT NOT NULL,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, date)
        )
    """)

    # 4) 레거시 사용자용 기본 프로필 보장 (마이그레이션 또는 신규 케이스 모두)
    conn.execute(
        "INSERT OR IGNORE INTO user_profile (user_id) VALUES (?)",
        (LEGACY_USER_ID,),
    )

    conn.commit()
    conn.close()


def _migrate_legacy_schema(conn: sqlite3.Connection):
    """단일사용자(인증 도입 전) 스키마 → 멀티사용자 스키마. 매 init_db()에서 안전 호출."""
    # ingredients — expiry_date / user_id 누락 시 보강
    if _table_exists(conn, "ingredients"):
        cols = _columns(conn, "ingredients")
        if "expiry_date" not in cols:
            conn.execute("ALTER TABLE ingredients ADD COLUMN expiry_date TEXT")
        if "user_id" not in cols:
            _recreate_ingredients(conn)

    # user_profile — id CHECK(id=1) 제약을 user_id PK로 변경
    if _table_exists(conn, "user_profile"):
        cols = _columns(conn, "user_profile")
        if "user_id" not in cols:
            _recreate_user_profile(conn)

    # saved_recipes — user_id 보강
    if _table_exists(conn, "saved_recipes"):
        cols = _columns(conn, "saved_recipes")
        if "user_id" not in cols:
            conn.execute(
                "ALTER TABLE saved_recipes ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1 "
                "REFERENCES users(id) ON DELETE CASCADE"
            )

    # shopping_list — name UNIQUE → (user_id, name) UNIQUE
    if _table_exists(conn, "shopping_list"):
        cols = _columns(conn, "shopping_list")
        if "user_id" not in cols:
            _recreate_shopping_list(conn)

    # daily_recipes — date PK → (user_id, date) PK
    if _table_exists(conn, "daily_recipes"):
        cols = _columns(conn, "daily_recipes")
        if "user_id" not in cols:
            _recreate_daily_recipes(conn)


def _recreate_ingredients(conn: sqlite3.Connection):
    conn.execute("ALTER TABLE ingredients RENAME TO _ingredients_old")
    conn.execute("""
        CREATE TABLE ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            category TEXT DEFAULT '기타',
            quantity TEXT,
            expiry_date TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'manual',
            UNIQUE(user_id, name)
        )
    """)
    old_cols = _columns(conn, "_ingredients_old")
    expiry_select = "expiry_date" if "expiry_date" in old_cols else "NULL"
    conn.execute(f"""
        INSERT INTO ingredients (id, user_id, name, category, quantity, expiry_date, added_at, source)
        SELECT id, {LEGACY_USER_ID}, name, category, quantity, {expiry_select}, added_at, source
        FROM _ingredients_old
    """)
    conn.execute("DROP TABLE _ingredients_old")


def _recreate_user_profile(conn: sqlite3.Connection):
    conn.execute("ALTER TABLE user_profile RENAME TO _user_profile_old")
    conn.execute("""
        CREATE TABLE user_profile (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            skill_level TEXT DEFAULT '초보',
            cuisine_preference TEXT DEFAULT '',
            taste_preference TEXT DEFAULT '',
            allergies TEXT DEFAULT ''
        )
    """)
    conn.execute(f"""
        INSERT INTO user_profile (user_id, skill_level, cuisine_preference, taste_preference, allergies)
        SELECT {LEGACY_USER_ID}, skill_level, cuisine_preference, taste_preference, allergies
        FROM _user_profile_old WHERE id = 1
    """)
    conn.execute("DROP TABLE _user_profile_old")


def _recreate_shopping_list(conn: sqlite3.Connection):
    conn.execute("ALTER TABLE shopping_list RENAME TO _shopping_list_old")
    conn.execute("""
        CREATE TABLE shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            quantity TEXT,
            category TEXT DEFAULT '기타',
            checked INTEGER DEFAULT 0,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
    """)
    conn.execute(f"""
        INSERT INTO shopping_list (id, user_id, name, quantity, category, checked, added_at)
        SELECT id, {LEGACY_USER_ID}, name, quantity, category, checked, added_at
        FROM _shopping_list_old
    """)
    conn.execute("DROP TABLE _shopping_list_old")


def _recreate_daily_recipes(conn: sqlite3.Connection):
    conn.execute("ALTER TABLE daily_recipes RENAME TO _daily_recipes_old")
    conn.execute("""
        CREATE TABLE daily_recipes (
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            recipes_json TEXT NOT NULL,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, date)
        )
    """)
    conn.execute(f"""
        INSERT INTO daily_recipes (user_id, date, recipes_json, generated_at)
        SELECT {LEGACY_USER_ID}, date, recipes_json, generated_at
        FROM _daily_recipes_old
    """)
    conn.execute("DROP TABLE _daily_recipes_old")
