from __future__ import annotations
from typing import Any, Dict, List, Optional


def _to_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(",", ".")
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


def _pick(row: Dict[str, Any], keys: List[str]) -> Any:
    """
    Busca keys ignorando mayúsculas, espacios y normalizando strings.
    """
    normalized = {}
    for k in row.keys():
        nk = str(k).strip().lower()
        normalized[nk] = k

    for wanted in keys:
        w = str(wanted).strip().lower()
        if w in normalized:
            real_key = normalized[w]
            val = row.get(real_key)
            if val not in (None, ""):
                return val
    return None


def compute_value_indicator_from_prob(
    odds: float,
    prob: float,
) -> float:
    """
    Indicador simple de 'value' basado en EV:
    EV = prob*(odds-1) - (1-prob)
       = prob*odds - 1
    """
    return (prob * odds) - 1.0


def build_opportunities(
    bets: List[Dict[str, Any]],
    limit: int = 50,
    min_value: float = 0.0,
) -> Dict[str, Any]:
    """
    Dataset actual: usa 'value' si existe; si no, intenta calcularlo con ('cuota' + 'prob').
    Compatible con filas dict o modelos Pydantic (Bet).
    """

    odds_keys = ["cuota", "odds", "price"]
    prob_keys = ["prob1", "prob", "probability"]
    value_keys = ["value", "edge", "ev"]

    out: List[Dict[str, Any]] = []
    skipped = 0

    for row in bets:
        # 🔴 CLAVE: normalizar Bet (Pydantic) → dict
        if not isinstance(row, dict):
            if hasattr(row, "model_dump"):       # Pydantic v2
                row = row.model_dump()
            elif hasattr(row, "dict"):           # Pydantic v1
                row = row.dict()
            else:
                skipped += 1
                continue

        # 1️⃣ Intentar usar 'value' directamente
        value = _to_float(_pick(row, value_keys))

        # 2️⃣ Si no hay 'value', calcularlo con cuota + prob
        if value is None:
            odds = _to_float(_pick(row, odds_keys))
            prob = _to_float(_pick(row, prob_keys))

            if odds is None or prob is None:
                skipped += 1
                continue

            value = (prob * odds) - 1.0

        # 3️⃣ Filtro por valor mínimo
        if value < min_value:
            continue

        # 4️⃣ Construir oportunidad
        out.append(
            {
                "id": row.get("id"),
                "fecha": row.get("fecha"),
                "deporte": row.get("deporte"),
                "bookie": row.get("bookie"),
                "evento": row.get("evento"),
                "mercado": row.get("mercado"),
                "cuota": _to_float(row.get("cuota")),
                "prob": _to_float(_pick(row, prob_keys)),
                "value": value,
                "kelly_f": _to_float(row.get("kelly_f")),
                "bankroll": _to_float(row.get("bankroll")),
                "stake": _to_float(row.get("stake")),
                "estado": row.get("estado"),
                "resultado": row.get("resultado"),
                "pnl": _to_float(row.get("pnl")),
            }
        )

    # Ordenar por value descendente
    out.sort(key=lambda x: x["value"], reverse=True)

    return {
        "count_in": len(bets),
        "count_out": min(len(out), limit),
        "skipped_missing_fields": skipped,
        "opportunities": out[: max(1, min(limit, 500))],
        "notes": [
            "Se usa 'value' del CSV si existe; si no, se calcula con value = prob*cuota - 1.",
            f"Filtradas por value >= {min_value}.",
        ],
    }

