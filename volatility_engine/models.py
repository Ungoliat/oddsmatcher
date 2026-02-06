# volatility_engine/models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

TeamSide = Literal["HOME", "AWAY"]
LeagueCode = Literal["EPL", "LL", "SA", "BL", "L1"]


@dataclass(frozen=True)
class Match:
    """
    Registro final del partido (1 fila por partido).
    """
    match_id: str
    date: str                 # "YYYY-MM-DD"
    league: LeagueCode        # EPL/LL/SA/BL/L1
    home: str
    away: str

    final_home_goals: int
    final_away_goals: int

    had_event: bool           # hubo +2 y luego igualdad


@dataclass(frozen=True)
class GoalEvent:
    """
    Un gol como evento, guardando el marcador *después* del gol.
    Ej: minuto 37, marca AWAY, marcador pasa a 1-2.
    """
    match_id: str
    minute: int               # 0-130 aprox (incluye añadido)
    side: TeamSide            # "HOME" o "AWAY"

    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class Plus2EqualizeEvent:
    """
    Info del patrón para un partido (puede ser None si no ocurre).
    """
    match_id: str

    minute_plus2: int
    score_at_plus2: str       # "2-0" o "1-3"
    side_with_plus2: TeamSide

    minute_equalized: int
    score_at_equalized: str   # "2-2" o "3-3"

    # útil para análisis luego
    final_score: Optional[str] = None  # "3-3", "4-3", etc.
