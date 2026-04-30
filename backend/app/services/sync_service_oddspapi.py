import json
from typing import Any, Dict, List, Set
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.models.event import Event

BOOKIE_SLUG_TO_NAME = {
    "betfair-ex": "betfair",
    "bwin.es": "bwin",
    "betsson": "betsson",
    "bet365": "bet365",
    "betway.es": "betway",
    "codere.es": "codere",
    "888sport.es": "888sport",
    "leovegas.es": "leovegas",
    "luckia.es": "luckia",
    "williamhill": "williamhill",
    "winamax.es": "winamax",
    "pokerstars.es": "pokerstars",
    "marcaapuestas": "marcaapuestas",
    "tonybet": "tonybet",
    "interwetten": "interwetten",
    "paf.es": "paf",
    "1xbet": "1xbet",
    "marathonbet": "marathonbet",
    "casumo": "casumo",
}

SPORT_SLUG_TO_DEPORTE = {
    "soccer": "football",
    "basketball": "basketball",
    "tennis": "tennis",
}

TOURNAMENT_NAMES = {
    8: "LaLiga",
    17: "Premier League",
    23: "Serie A",
    34: "Ligue 1",
    35: "Bundesliga",
}


def sync_events_from_oddspapi(db: Session, provider) -> Dict[str, Any]:
    payload = provider.fetch_events()
    raw_events: List[Dict[str, Any]] = payload.get("events", [])

    db.query(Event).delete()
    db.commit()

    existing_keys: Set[str] = set()
    inserted = 0
    skipped = 0
    prepared_rows = []

    for raw_event in raw_events:
        home_team = raw_event.get("home_team", "")
        away_team = raw_event.get("away_team", "")
        sport = raw_event.get("sport", "soccer")
        tournament_id = raw_event.get("tournament_id")
        start_time_str = raw_event.get("start_time")
        bookmakers = raw_event.get("bookmakers", {})

        if not home_team or not away_team:
            skipped += 1
            continue

        partido = f"{home_team} vs {away_team}"
        deporte = SPORT_SLUG_TO_DEPORTE.get(sport, sport)
        competicion = TOURNAMENT_NAMES.get(tournament_id, f"Tournament {tournament_id}")

        commence_time = None
        if start_time_str:
            try:
                commence_time = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00")
                )
            except Exception:
                pass

        for bookie_slug, markets in bookmakers.items():
            bookie = BOOKIE_SLUG_TO_NAME.get(bookie_slug, bookie_slug)

            if not markets:
                skipped += 1
                continue

            mercados = sorted(markets.keys())
            dedupe_key = "||".join([
                bookie.lower(),
                competicion.lower(),
                partido.lower(),
                ",".join(mercados).lower(),
                deporte.lower(),
            ])

            if dedupe_key in existing_keys:
                skipped += 1
                continue

            event = Event(
                bookie=bookie,
                competicion=competicion,
                partido=partido,
                mercados=json.dumps(mercados, ensure_ascii=False),
                deporte=deporte,
                commence_time=commence_time,
                home_team=home_team,
                away_team=away_team,
                cuotas=json.dumps(markets, ensure_ascii=False),
            )

            prepared_rows.append(event)
            existing_keys.add(dedupe_key)
            inserted += 1

    if prepared_rows:
        db.add_all(prepared_rows)
        db.commit()

    return {
        "provider": "oddspapi",
        "inserted": inserted,
        "skipped": skipped,
        "total_raw_events": len(raw_events),
        "meta": payload.get("meta", {}),
    }