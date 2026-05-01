import json
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.event import Event

from app.core.bookies import (
    BOOKIES_ES_ALLOWED_EXACT,
    canonicalize_bookie_name,
)

SPORT_KEY_TO_DEPORTE = {
    "soccer": "football",
    "basketball": "basketball",
    "tennis": "tennis",
    "baseball": "baseball",
    "americanfootball": "americanfootball",
    "icehockey": "icehockey",
}

MARKET_KEY_TO_LABEL = {
    "h2h": "1X2",
    "spreads": "SPREADS",
    "totals": "OU",
    "btts": "BTTS",
}


# ------------------------
# NORMALIZADORES
# ------------------------

def normalize_deporte(sport_key: str) -> str:
    prefix = (sport_key or "").split("_")[0].lower()
    return SPORT_KEY_TO_DEPORTE.get(prefix, prefix or "unknown")


def normalize_partido(home_team: str, away_team: str) -> str:
    return f"{(home_team or '').strip()} vs {(away_team or '').strip()}"


def normalize_mercados(bookmaker: Dict[str, Any]) -> List[str]:
    market_keys = []

    for market in bookmaker.get("markets", []):
        key = (market.get("key") or "").strip().lower()

        if not key or key == "h2h_lay":
            continue

        market_keys.append(MARKET_KEY_TO_LABEL.get(key, key.upper()))

    return sorted(set(market_keys))


# ------------------------
# CUOTAS 1X2 LIMPIAS
# ------------------------

def safe_float_price(value):
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None

    if price <= 1.01 or price > 100:
        return None

    return price


def normalize_1x2_cuotas(
    home_team: str,
    away_team: str,
    bookmaker: Dict[str, Any],
) -> Dict[str, float] | None:

    home_norm = (home_team or "").strip().lower()
    away_norm = (away_team or "").strip().lower()

    if not home_norm or not away_norm:
        return None

    for market in bookmaker.get("markets", []):
        key = (market.get("key") or "").strip().lower()

        if key != "h2h":
            continue

        cuotas = {}

        for outcome in market.get("outcomes", []):
            name = (outcome.get("name") or "").strip()
            name_norm = name.lower()
            price = safe_float_price(outcome.get("price"))

            if price is None:
                continue

            if name_norm == home_norm:
                cuotas["1"] = price
            elif name_norm == away_norm:
                cuotas["2"] = price
            elif name_norm in {"draw", "tie", "empate", "x"}:
                cuotas["X"] = price

        if set(cuotas.keys()) == {"1", "X", "2"}:
            return cuotas

    return None


def is_suspicious_1x2_cuotas(cuotas: Dict[str, float]) -> bool:
    o1 = cuotas["1"]
    ox = cuotas["X"]
    o2 = cuotas["2"]

    if o1 > 20 or ox > 20 or o2 > 20:
        return True

    inv_sum = (1 / o1) + (1 / ox) + (1 / o2)

    if inv_sum < 0.80:
        return True

    return False


# ------------------------
# DEDUPE
# ------------------------

def build_dedupe_key(
    bookie: str,
    competicion: str,
    partido: str,
    mercados,
    deporte: str,
) -> str:
    return "||".join(
        [
            (bookie or "").strip().lower(),
            (competicion or "").strip().lower(),
            (partido or "").strip().lower(),
            ",".join(sorted(mercados)).lower()
            if isinstance(mercados, list)
            else (mercados or "").strip().lower(),
            (deporte or "").strip().lower(),
        ]
    )


# ------------------------
# MAIN SYNC
# ------------------------

def sync_events_from_provider(db: Session, provider) -> Dict[str, Any]:
    payload = provider.fetch_events()
    raw_events: List[Dict[str, Any]] = payload.get("events", [])

    db.query(Event).delete()
    db.commit()

    existing_keys: Set[str] = set()

    inserted = 0
    skipped = 0
    skipped_not_allowed_bookie = 0
    skipped_duplicates = 0
    skipped_invalid_1x2 = 0
    skipped_suspicious_1x2 = 0

    prepared_rows = []

    for raw_event in raw_events:
        sport_key = raw_event.get("sport_key", "")
        sport_title = raw_event.get("sport_title", "")
        home_team = raw_event.get("home_team", "")
        away_team = raw_event.get("away_team", "")
        bookmakers = raw_event.get("bookmakers", [])

        deporte = normalize_deporte(sport_key)
        competicion = sport_title.strip() if sport_title else sport_key
        partido = normalize_partido(home_team, away_team)

        commence_time = None
        commence_time_raw = raw_event.get("commence_time")
        if commence_time_raw:
            try:
                commence_time = datetime.fromisoformat(
                    commence_time_raw.replace("Z", "+00:00")
                )
            except Exception:
                pass

        for bookmaker in bookmakers:
            raw_bookie = (bookmaker.get("title") or bookmaker.get("key") or "").strip()

            if not raw_bookie or not partido:
                skipped += 1
                continue

            bookie = canonicalize_bookie_name(raw_bookie)

            if not bookie:
                skipped += 1
                skipped_not_allowed_bookie += 1
                continue

            mercados = ["1X2"]  # ahora solo trabajamos limpio

            dedupe_key = build_dedupe_key(
                bookie, competicion, partido, mercados, deporte
            )

            if dedupe_key in existing_keys:
                skipped += 1
                skipped_duplicates += 1
                continue

            cuotas_1x2 = normalize_1x2_cuotas(
                home_team, away_team, bookmaker
            )

            if cuotas_1x2 is None:
                skipped += 1
                skipped_invalid_1x2 += 1
                continue

            if is_suspicious_1x2_cuotas(cuotas_1x2):
                skipped += 1
                skipped_suspicious_1x2 += 1
                continue

            cuotas = {
                "1X2": cuotas_1x2
            }

            event = Event(
                bookie=bookie,
                competicion=competicion,
                partido=partido,
                mercados=json.dumps(mercados, ensure_ascii=False),
                deporte=deporte,
                cuotas=json.dumps(cuotas, ensure_ascii=False),
                commence_time=commence_time,
            )

            prepared_rows.append(event)
            existing_keys.add(dedupe_key)
            inserted += 1

    if prepared_rows:
        db.add_all(prepared_rows)
        db.commit()

    return {
        "provider": payload.get("provider"),
        "inserted": inserted,
        "skipped": skipped,
        "skipped_not_allowed_bookie": skipped_not_allowed_bookie,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid_1x2": skipped_invalid_1x2,
        "skipped_suspicious_1x2": skipped_suspicious_1x2,
        "total_raw_events": len(raw_events),
        "bookies_es_allowed": sorted(list(BOOKIES_ES_ALLOWED_EXACT)),
        "meta": payload.get("meta", {}),
    }