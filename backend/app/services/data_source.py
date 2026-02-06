import csv
from pathlib import Path
from typing import List, Dict, Union

from app.services.normalize_service import normalize_row


def load_events_from_csv(csv_path: Union[str, Path]) -> List[Dict]:
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV: {path}")

    events: List[Dict] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=1):
            try:
                # 🔥 D5: normalizamos aquí
                normalized = normalize_row(row)
                events.append(normalized)
            except Exception as e:
                raise ValueError(f"Error en fila {i}: {row}. Detalle: {e}") from e

    return events
