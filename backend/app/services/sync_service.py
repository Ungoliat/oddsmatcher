from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from app.models.event import Event


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


def normalize_mercados(bookmaker: Dict[str, Any]) -> str:
    market_keys = []

    for market in bookmaker.get("markets", []):
        key = (market.get("key") or "").strip().lower()
        if key:
            market_keys.append(MARKET_KEY_TO_LABEL.get(key, key.upper()))

    unique_markets = sorted(set(market_keys))
    return ", ".join(unique_markets)


def build_dedupe_key(
    bookie: str,
    competicion: str,
    partido: str,
    mercados: str,
    deporte: str,
) -> str:
    return "||".join(
        [
            (bookie or "").strip().lower(),
            (competicion or "").strip().lower(),
            (partido or "").strip().lower(),
            (mercados or "").strip().lower(),
            (deporte or "").strip().lower(),
        ]
    )


def sync_events_from_provider(db: Session, provider) -> Dict[str, Any]:
    payload = provider.fetch_events()
    raw_events: List[Dict[str, Any]] = payload.get("events", [])

    existing_rows = db.query(
        Event.bookie,
        Event.competicion,
        Event.partido,
        Event.mercados,
        Event.deporte,
    ).all()

    existing_keys: Set[str] = {
        build_dedupe_key(
            row.bookie,
            row.competicion,
            row.partido,
            row.mercados,
            row.deporte,
        )
        for row in existing_rows
    }

    inserted = 0
    skipped = 0
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

        for bookmaker in bookmakers:
            bookie = (bookmaker.get("title") or bookmaker.get("key") or "").strip()
            mercados = normalize_mercados(bookmaker)

            if not bookie or not partido:
                skipped += 1
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
                continue

            event = Event(
                bookie=bookie,
                competicion=competicion,
                partido=partido,
                mercados=mercados,
                deporte=deporte,
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
        "total_raw_events": len(raw_events),
        "meta": payload.get("meta", {}),
    }