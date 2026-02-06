from pathlib import Path
import sqlite3

# Guardamos la DB en backend/data/oddsmatcher.db (misma idea que el CSV)
BASE_DIR = Path(__file__).resolve().parents[2]  # .../backend
DB_PATH = BASE_DIR / "data" / "oddsmatcher.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL,
                disabled INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
