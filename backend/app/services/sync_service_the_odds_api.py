import json
from typing import Any, Dict, List, Set
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.models.event import Event

# Mapa de sport_key de The Odds API → nombre interno
SPORT_KEY_TO_DEPORTE = {
    "soccer_spain_la_liga": "football",
    "soccer_spain_segunda_division": "football",
    "soccer_epl": "football",
    "soccer_germany_bundesliga": "football",
    "soccer_italy_serie_a": "football",
    "soccer_france_ligue_one": "football",
    "soccer_uefa_champs_league": "football",
    "soccer_europa_league": "football",
    "soccer_uefa_europa_conference_league": "football",
    "tennis_atp_french_open": "tennis",
    "tennis_wta_french_open": "tennis",
    "basketball_nba": "basketball",
    "basketball_euroleague": "basketball",
}

# Mapa de sport_key → nombre de competición legible
SPORT_KEY_TO_COMPETICION = {
    "soccer_spain_la_liga": "LaLiga",
    "soccer_spain_segunda_division": "Segunda División",
    "soccer_epl": "Premier League",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_italy_serie_a": "Serie A",
    "soccer_france_ligue_one": "Ligue 1",
    "soccer_uefa_champs_league": "Champions League",
    "soccer_europa_league": "Europa League",
    "soccer_uefa_europa_conference_league": "Conference League",
    "tennis_atp_french_open": "ATP French Open",
    "tennis_wta_french_open": "WTA French Open",
    "basketball_nba": "NBA",
    "basketball_euroleague": "Euroleague",
}

# Mapa de bookmaker key de The Odds API → nombre interno
BOOKIE_KEY_TO_NAME = {
    "betfair_ex_eu": "betfair",
    "betfair_ex_uk": "betfair",
    "bwin": "bwin",
    "betsson": "betsson",
    "bet365": "bet365",
    "betway": "betway",
    "unibet_eu": "unibet",
    "williamhill": "williamhill",
    "paddypower": "paddypower",
    "betvictor": "betvictor",
    "marathonbet": "marathonbet",
    "casumo": "casumo",
    "888sport": "888sport",
    "suprabets": "suprabets",
    "winamax_fr": "winamax",
    "pokerstars": "pokerstars",
    "onexbet": "1xbet",
    "tipico_de": "tipico",
    "ladbrokes_eu": "ladbrokes",
    "coral": "coral",
}

# Mapa de market key de The Odds API → nombre interno
MARKET_KEY_TO_LABEL = {
    "h2h": "1X2",
    "totals": "OU2.5",
    "spreads": "AH",
    "btts": "BTTS",
    "double_chance": "DC",
}


def _parse_markets(bookmaker: Dict) -> Dict[str, Dict[str, float]]:
    """
    Transforma los markets de un bookmaker de The Odds API al formato interno:
    { "1X2": {"home": 1.85, "draw": 3.40, "away": 4.50}, ... }
    """
    result = {}

    for market in bookmaker.get("markets", []):
        market_key = market.get("key", "")
        market_label = MARKET_KEY_TO_LABEL.get(market_key)
        if not market_label:
            continue

        outcomes_raw = market.get("outcomes", [])
        outcomes = {}

        for outcome in outcomes_raw:
            name = outcome.get("name", "")
            price = outcome.get("price")
            point = outcome.get("point")  # para OU y AH

            if not name or not price or price <= 1:
                continue

            # Normalizar nombres de outcomes
            name_lower = name.lower()
            if market_label == "1X2":
                if name_lower in ("home", "1"):
                    key = "home"
                elif name_lower in ("draw", "x"):
                    key = "draw"
                elif name_lower in ("away", "2"):
                    key = "away"
                else:
                    key = name
            elif market_label in ("OU2.5", "totals"):
                suffix = f" {point}" if point is not None else ""
                key = f"Over{suffix}" if "over" in name_lower else f"Under{suffix}"
            elif market_label == "BTTS":
                key = "Yes" if "yes" in name_lower else "No"
            elif market_label == "DC":
                if "home" in name_lower and "draw" in name_lower:
                    key = "1X"
                elif "home" in name_lower and "away" in name_lower:
                    key = "12"
                elif "draw" in name_lower and "away" in name_lower:
                    key = "X2"
                else:
                    key = name
            else:
                key = name

            outcomes[key] = price

        if outcomes:
            result[market_label] = outcomes

    return result


def sync_events_from_the_odds_api(db: Session, provider) -> Dict[str, Any]:
    payload = provider.fetch_events()
    raw_events: List[Dict[str, Any]] = payload.get("events", [])

    # Borrar solo eventos de The Odds API para no pisar OddsPapi/Betfair
    db.query(Event).filter(Event.source == "the_odds_api").delete()
    db.commit()

    existing_keys: Set[str] = set()
    inserted = 0
    skipped = 0
    prepared_rows = []

    for raw_event in raw_events:
        sport_key = raw_event.get("sport_key", "")
        home_team = raw_event.get("home_team", "")
        away_team = raw_event.get("away_team", "")
        commence_time_str = raw_event.get("commence_time")
        bookmakers_raw = raw_event.get("bookmakers", [])

        if not home_team or not away_team:
            skipped += 1
            continue

        partido = f"{home_team} vs {away_team}"
        deporte = SPORT_KEY_TO_DEPORTE.get(sport_key, "football")
        competicion = SPORT_KEY_TO_COMPETICION.get(sport_key, sport_key)

        commence_time = None
        if commence_time_str:
            try:
                commence_time = datetime.fromisoformat(
                    commence_time_str.replace("Z", "+00:00")
                )
            except Exception:
                pass

        for bookmaker in bookmakers_raw:
            bookie_key = bookmaker.get("key", "")
            bookie = BOOKIE_KEY_TO_NAME.get(bookie_key, bookie_key)

            markets = _parse_markets(bookmaker)
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
                source="the_odds_api",
            )

            prepared_rows.append(event)
            existing_keys.add(dedupe_key)
            inserted += 1

    if prepared_rows:
        db.add_all(prepared_rows)
        db.commit()

    return {
        "provider": "the_odds_api",
        "inserted": inserted,
        "skipped": skipped,
        "total_raw_events": len(raw_events),
        "meta": payload.get("meta", {}),
    }