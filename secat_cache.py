import json
import os
import time
from datetime import datetime, timezone, timedelta

CACHE_DIR = "cache"

# Cache expiry times
OFFERINGS_CACHE_SECONDS = 60 * 60 * 24 * 7      # 7 days
SECAT_DATA_CACHE_SECONDS = 60 * 60 * 24 * 30    # 30 days
MARKET_CACHE_SECONDS = 60 * 60 * 24 * 7

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool = None
_pool_init_failed = False


def _get_pool():
    global _pool, _pool_init_failed

    if _pool_init_failed or DATABASE_URL is None:
        return None

    if _pool is not None:
        return _pool

    try:
        import psycopg2.pool

        url = DATABASE_URL
        # Heroku uses postgres://, psycopg2 requires postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        _pool = psycopg2.pool.ThreadedConnectionPool(1, 5, url)

        conn = _pool.getconn()
        try:
            _ensure_schema(conn)
            conn.commit()
        finally:
            _pool.putconn(conn)

        print("[DB] PostgreSQL cache pool initialized")
        return _pool
    except Exception as e:
        print(f"[DB] Pool init failed: {e}")
        _pool_init_failed = True
        return None


def _ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


def _db_get(key: str, max_age_seconds: int):
    db_pool = _get_pool()
    if db_pool is None:
        return None

    conn = None
    try:
        conn = db_pool.getconn()
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data FROM cache_entries WHERE key = %s AND created_at > %s",
                (key, cutoff),
            )
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"[DB] Read error ({key}): {e}")
        return None
    finally:
        if conn is not None:
            db_pool.putconn(conn)


def _db_set(key: str, data) -> bool:
    db_pool = _get_pool()
    if db_pool is None:
        return False

    conn = None
    try:
        import psycopg2.extras

        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cache_entries (key, data, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE
                    SET data = EXCLUDED.data, created_at = NOW()
                """,
                (key, psycopg2.extras.Json(data)),
            )
        conn.commit()
        return True
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"[DB] Write error ({key}): {e}")
        return False
    finally:
        if conn is not None:
            db_pool.putconn(conn)


# --- File cache fallback ---

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def safe_filename(value: str):
    return (
        value.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace(",", "_")
        .replace(" ", "_")
    )


def cache_path(key: str):
    ensure_cache_dir()
    return os.path.join(CACHE_DIR, safe_filename(key) + ".json")


def is_cache_valid(path: str, max_age_seconds: int):
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) <= max_age_seconds


def _file_get(key: str, max_age_seconds: int):
    path = cache_path(key)
    if not is_cache_valid(path, max_age_seconds):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _file_set(key: str, data):
    path = cache_path(key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# --- Public API ---

def get_cached_json(key: str, max_age_seconds: int):
    result = _db_get(key, max_age_seconds)
    if result is not None:
        return result
    return _file_get(key, max_age_seconds)


def set_cached_json(key: str, data):
    if not _db_set(key, data):
        _file_set(key, data)
