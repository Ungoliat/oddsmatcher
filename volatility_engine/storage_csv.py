# volatility_engine/storage_csv.py
import csv
from pathlib import Path
from typing import List

from .models import GoalEvent, Match


DATA_DIR = Path(__file__).resolve().parent / "data"


def read_goal_events(path: Path) -> List[GoalEvent]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    events: List[GoalEvent] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append(
                GoalEvent(
                    match_id=row["match_id"],
                    minute=int(row["minute"]),
                    side=row["side"],
                    home_goals=int(row["home_goals"]),
                    away_goals=int(row["away_goals"]),
                )
            )

    # MUY IMPORTANTE: orden cronológico
    events.sort(key=lambda e: (e.match_id, e.minute))
    return events


def append_match(path: Path, row: list, header: list) -> None:
    """
    Escribe una fila en el CSV.
    - row: lista de valores
    - header: cabecera del CSV (se escribe solo si el archivo no existe)
    """
    is_new = not path.exists()

    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(header)
        writer.writerow(row)

