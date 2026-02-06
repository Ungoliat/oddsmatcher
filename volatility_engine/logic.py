# volatility_engine/logic.py
from __future__ import annotations

from typing import List, Optional, Tuple

from .models import GoalEvent, Plus2EqualizeEvent, TeamSide


def detect_plus2_equalize(match_id: str, events: List[GoalEvent]) -> Optional[Plus2EqualizeEvent]:
    """
    Devuelve un Plus2EqualizeEvent si ocurre el patrón:
    aparece una ventaja de +2 (en cualquier momento) y luego se iguala (diff=0).
    Si no ocurre, devuelve None.

    events debe ser la lista de goles de UN partido.
    """

    # Aseguramos orden por minuto (por si acaso)
    events = sorted(events, key=lambda e: e.minute)

    plus2_seen = False
    minute_plus2: Optional[int] = None
    score_plus2: Optional[str] = None
    side_with_plus2: Optional[TeamSide] = None

    for e in events:
        diff = e.home_goals - e.away_goals

        # Detectar el primer momento donde hay ventaja de 2 o más
        if not plus2_seen and abs(diff) >= 2:
            plus2_seen = True
            minute_plus2 = e.minute
            score_plus2 = f"{e.home_goals}-{e.away_goals}"
            side_with_plus2 = "HOME" if diff > 0 else "AWAY"
            continue

        # Una vez visto el +2, si luego se iguala (diff==0), evento completado
        if plus2_seen and diff == 0:
            return Plus2EqualizeEvent(
                match_id=match_id,
                minute_plus2=minute_plus2 if minute_plus2 is not None else -1,
                score_at_plus2=score_plus2 if score_plus2 is not None else "",
                side_with_plus2=side_with_plus2 if side_with_plus2 is not None else "HOME",
                minute_equalized=e.minute,
                score_at_equalized=f"{e.home_goals}-{e.away_goals}",
            )

    return None
