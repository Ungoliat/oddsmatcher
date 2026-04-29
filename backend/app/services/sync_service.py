import json
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

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


def normalize_deporte(sport_key: str) -> str:
    prefix = (sport_key or "").split("_")[0].lower()
    return SPORT_KEY_TO_DEPORTE.get(prefix, prefix or "unknown")


def normalize_partido(home_team: str, away_team: str) -> str:
    home = (home_team or "").strip()
    away = (away_team or "").strip()
    return f"{home} vs {away}"


def normalize_mercados(bookmaker: Dict[str, Any]) -> List[str]:
    market_keys = []

    for market in bookmaker.get("markets", []):
        key = (market.get("key") or "").strip().lower()

        if not key:
            continue

        if key == "h2h_lay":
            continue

        market_keys.append(MARKET_KEY_TO_LABEL.get(key, key.upper()))

    return sorted(set(market_keys))


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
            ",".join(sorted(mercados)).lower() if isinstance(mercados, list) else (mercados or "").strip().lower(),
            (deporte or "").strip().lower(),
        ]
    )

def extract_cuotas(bookmaker: Dict[str, Any]) -> Dict[str, Any]:
    cuotas = {}

    for market in bookmaker.get("markets", []):
        key = (market.get("key") or "").strip().lower()

        if not key or key == "h2h_lay":
            continue

        label = MARKET_KEY_TO_LABEL.get(key, key.upper())
        outcomes = {}

        for outcome in market.get("outcomes", []):
            name = (outcome.get("name") or "").strip()
            price = outcome.get("price")
            if name and price is not None:
                outcomes[name] = price

        if outcomes:
            cuotas[label] = outcomes

    return cuotas

def sync_events_from_provider(db: Session, provider) -> Dict[str, Any]:
    payload = provider.fetch_events()
    raw_events: List[Dict[str, Any]] = payload.get("events", [])

    # Reemplazo total del dataset
    db.query(Event).delete()
    db.commit()

    # Como acabamos de vaciar la tabla, arrancamos sin claves previas
    existing_keys: Set[str] = set()

    inserted = 0
    skipped = 0
    skipped_not_allowed_bookie = 0
    skipped_duplicates = 0
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

        commence_time_raw = raw_event.get("commence_time")
        from datetime import datetime, timezone
        commence_time = None
        if commence_time_raw:
            try:
                commence_time = datetime.fromisoformat(
                    commence_time_raw.replace("Z", "+00:00")
                )
            except Exception:
                commence_time = None

        for bookmaker in bookmakers:
            bookie = (bookmaker.get("title") or bookmaker.get("key") or "").strip()
            mercados = normalize_mercados(bookmaker)

            if not bookie or not partido:
                skipped += 1
                continue

            # Filtro bookies útiles para España
            raw_bookie = (bookmaker.get("title") or bookmaker.get("key") or "").strip()
            mercados = normalize_mercados(bookmaker)

            if not raw_bookie or not partido:
                skipped += 1
                continue

            bookie = canonicalize_bookie_name(raw_bookie)

            if not bookie:
                skipped += 1
                skipped_not_allowed_bookie += 1
                continue    

            dedupe_key = build_dedupe_key(
                bookie=bookie,
                competicion=competicion,
                partido=partido,
                mercados=mercados,
                deporte=deporte,
            )

            if dedupe_key in existing_keys:
                skipped += 1
                skipped_duplicates += 1
                continue

            cuotas = extract_cuotas(bookmaker)

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
        "total_raw_events": len(raw_events),
        "bookies_es_allowed": sorted(list(BOOKIES_ES_ALLOWED_EXACT)),
        "meta": payload.get("meta", {}),
    }