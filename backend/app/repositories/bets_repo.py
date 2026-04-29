from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.db.database import get_conn


def create_bet(username: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO bets (
                username, fecha_registro, notas, partido, competicion,
                fecha_evento, outcome, mercado, bookie,
                back_odds, lay_odds, stake_back, stake_lay,
                resultado_estimado, resultado_real, estado, tipo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                now,
                data.get("notas", ""),
                data["partido"],
                data.get("competicion", ""),
                data.get("fecha_evento"),
                data["outcome"],
                data.get("mercado", ""),
                data["bookie"],
                data["back_odds"],
                data["lay_odds"],
                data["stake_back"],
                data["stake_lay"],
                data.get("resultado_estimado"),
                data.get("resultado_real"),
                data.get("estado", "pendiente"),
                data.get("tipo", "MB"),
            ),
        )
        conn.commit()
        return get_bet(cursor.lastrowid)


def get_bet(bet_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM bets WHERE id = ?", (bet_id,)
        ).fetchone()
        return dict(row) if row else None


def list_bets(username: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM bets WHERE username = ? ORDER BY fecha_registro DESC",
            (username,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_bet(bet_id: int, username: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE bets SET
                notas = ?,
                resultado_real = ?,
                estado = ?,
                tipo = ?
            WHERE id = ? AND username = ?
            """,
            (
                data.get("notas"),
                data.get("resultado_real"),
                data.get("estado", "pendiente"),
                data.get("tipo", "MB"),
                bet_id,
                username,
            ),
        )
        conn.commit()
        return get_bet(bet_id)


def delete_bet(bet_id: int, username: str) -> bool:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM bets WHERE id = ? AND username = ?",
            (bet_id, username),
        )
        conn.commit()
        return True