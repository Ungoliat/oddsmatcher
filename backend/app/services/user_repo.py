from typing import Optional, List, Dict, Any

from app.db.database import get_conn


def get_user_row(username: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT username, hashed_password, role, disabled FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def upsert_user(username: str, hashed_password: str, role: str, disabled: bool = False) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (username, hashed_password, role, disabled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                hashed_password = excluded.hashed_password,
                role = excluded.role,
                disabled = excluded.disabled
            """,
            (username, hashed_password, role, 1 if disabled else 0),
        )
        conn.commit()


def list_users() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, role, disabled FROM users ORDER BY username ASC"
        ).fetchall()
        return [dict(r) for r in rows]
