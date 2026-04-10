import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "culinary.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT '기타',
            quantity TEXT,
            expiry_date TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'manual'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            skill_level TEXT DEFAULT '초보',
            cuisine_preference TEXT DEFAULT '',
            taste_preference TEXT DEFAULT '',
            allergies TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO user_profile (id) VALUES (1)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            name TEXT UNIQUE NOT NULL,
            quantity TEXT,
            category TEXT DEFAULT '기타',
            checked INTEGER DEFAULT 0,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 기존 ingredients 테이블에 expiry_date 컬럼이 없으면 추가
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(ingredients)").fetchall()]
    if "expiry_date" not in columns:
        conn.execute("ALTER TABLE ingredients ADD COLUMN expiry_date TEXT")

    conn.commit()
    conn.close()
