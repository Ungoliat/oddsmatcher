import json
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from app.models.event import Event
from app.core.normalizer import emparejar_partido


def sync_betfair_odds(db: Session, provider) -> Dict[str, Any]:
    """
    Obtiene cuotas de Betfair Exchange y las fusiona con los eventos
    existentes en la DB añadiendo las cuotas de lay.
    """
    betfair_events = provider.fetch_odds()

    if not betfair_events:
        return {"provider": "betfair", "updated": 0, "error": "No data"}


    # Obtener todos los eventos actuales de la DB
    db_events = db.query(Event).all()

    # Crear mapa partido → eventos DB
    partido_map: Dict[str, List[Event]] = {}
    for event in db_events:
        partido_map.setdefault(event.partido, []).append(event)

    partidos_db = list(partido_map.keys())
    updated = 0
    skipped = 0

    for bf_event in betfair_events:
        partido_bf = bf_event["partido"]
        odds_bf = bf_event["odds"]

        # Emparejar con partido en DB
        partido_match = emparejar_partido(partido_bf, partidos_db)

        if not partido_match:
            skipped += 1
            continue
        
        if "Wolves" in partido_bf or "Fulham" in partido_bf:
            print(f"DEBUG SYNC partido_bf: {partido_bf}")
            print(f"DEBUG SYNC partido_match: {partido_match}")
            print(f"DEBUG SYNC odds_bf: {odds_bf}")

        # Obtener eventos de la DB para este partido
        eventos_db = partido_map.get(partido_match, [])

        # Buscar si ya existe una entrada de betfair o crear una nueva
        betfair_event = next((e for e in eventos_db if e.bookie == "betfair"), None)

        # Extraer equipos del partido matcheado
        from rapidfuzz import fuzz
        partes = partido_match.split(" vs ")
        home_team = partes[0].strip() if len(partes) == 2 else ""
        away_team = partes[1].strip() if len(partes) == 2 else ""

        if "Wolverhampton" in partido_match:
            print(f"DEBUG home: '{home_team}', away: '{away_team}'")
            for key, price in odds_bf.items():
                if key.startswith("lay_"):
                    outcome = key.replace("lay_", "")
                    r_home = fuzz.ratio(outcome.lower(), home_team.lower())
                    r_away = fuzz.ratio(outcome.lower(), away_team.lower())
                    print(f"  outcome='{outcome}' ratio_home={r_home} ratio_away={r_away}")

        # Construir cuotas normalizadas mapeando nombres cortos al nombre completo
        cuotas = {"1X2": {}}
        for key, price in odds_bf.items():
            if key.startswith("lay_"):
                outcome = key.replace("lay_", "")
                if outcome == "draw":
                    cuotas["1X2"]["draw"] = price
                elif home_team and (
                    fuzz.partial_ratio(outcome.lower(), home_team.lower()) > 80 or
                    home_team.lower().startswith(outcome.lower())
                ):
                    cuotas["1X2"][home_team] = price
                elif away_team and (
                    fuzz.partial_ratio(outcome.lower(), away_team.lower()) > 80 or
                    away_team.lower().startswith(outcome.lower())
                ):
                    cuotas["1X2"][away_team] = price
                else:
                    cuotas["1X2"][outcome] = price

        if betfair_event:
            # Actualizar cuotas existentes
            betfair_event.cuotas = json.dumps(cuotas, ensure_ascii=False)
            updated += 1
        else:
            # Crear nueva entrada para betfair
            ref = eventos_db[0] if eventos_db else None
            new_event = Event(
                bookie="betfair",
                competicion=bf_event.get("competicion", ""),
                partido=partido_match,
                mercados=json.dumps(["1X2"], ensure_ascii=False),
                deporte="football",
                commence_time=ref.commence_time if ref else None,
                home_team=ref.home_team if ref else "",
                away_team=ref.away_team if ref else "",
                cuotas=json.dumps(cuotas, ensure_ascii=False),
            )
            db.add(new_event)
            updated += 1

    db.commit()

    return {
        "provider": "betfair",
        "updated": updated,
        "skipped": skipped,
        "total_betfair_events": len(betfair_events),
    }