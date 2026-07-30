import json
import time
from typing import Any, Dict, Set
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.models.event import Event

# IDs de torneos de Winamax que nos interesan
# sport_id=1 es fútbol, categoryId=7 es Francia
TORNEOS_INTERES = {
    4: ("Ligue 1", "football"),
    19: ("Ligue 2", "football"),
    36: ("LaLiga", "football"),
    37: ("Segunda División", "football"),
    1: ("Premier League", "football"),
    42: ("Bundesliga", "football"),
    33: ("Serie A", "football"),
    34: ("Serie B", "football"),
    38: ("Jupiler Pro League", "football"),
    39: ("Eredivisie", "football"),
    52: ("Liga Portugal", "football"),
    62: ("Süper Lig", "football"),
    151665: ("Champions League", "football"),
    10909: ("Europa League", "football"),
    151677: ("Conference League", "football"),
    177: ("NBA", "basketball"),
    153: ("Euroleague", "basketball"),
    175549: ("ATP Roland Garros", "tennis"),
    151307: ("WTA Roland Garros", "tennis"),
}


URLS_LIGAS = [
    ("https://www.winamax.es/apuestas-deportivas/sports/1/32/36", "LaLiga"),
    ("https://www.winamax.es/apuestas-deportivas/sports/1/7/4", "Ligue 1"),
    ("https://www.winamax.es/apuestas-deportivas/sports/1/1/1", "Premier League"),
    ("https://www.winamax.es/apuestas-deportivas/sports/1/31/33", "Serie A"),
    ("https://www.winamax.es/apuestas-deportivas/sports/1/30/42", "Bundesliga"),
]

def _capturar_datos_winamax() -> Dict:
    from playwright.sync_api import sync_playwright

    datos_total = {}

    for url, nombre in URLS_LIGAS:
        print(f"[Winamax] Capturando {nombre}...")
        mensajes = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )

                def on_websocket(ws):
                    def on_message(payload):
                        if len(payload) > 5000 and "matches" in payload:
                            mensajes.append(payload)
                    ws.on("framereceived", on_message)

                page.on("websocket", on_websocket)
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(25)
                browser.close()

        except Exception as e:
            print(f"[Winamax] Error en {nombre}: {e}")
            continue

        for msg in mensajes:
            try:
                json_str = msg[7:-1]
                data = json.loads(json_str)
                if "matches" in data and "bets" in data:
                    for key in ("matches", "bets", "outcomes", "odds", "tournaments"):
                        if key in data:
                            datos_total.setdefault(key, {}).update(data[key])
            except Exception:
                continue

    return datos_total


def sync_events_from_winamax(db: Session) -> Dict[str, Any]:
    """
    Sincroniza eventos de Winamax en la base de datos.
    """
    print("[Winamax] Iniciando captura de datos via Playwright...")
    datos = _capturar_datos_winamax()

    matches = datos.get("matches", {})
    tournaments = datos.get("tournaments", {})

    if not matches:
        return {
            "provider": "winamax",
            "inserted": 0,
            "skipped": 0,
            "error": "No se capturaron datos del WebSocket",
        }

    print(f"[Winamax] Datos capturados: {len(matches)} partidos")

    # Borrar eventos anteriores de Winamax
    db.query(Event).filter(Event.source == "winamax_fr").delete()
    db.commit()

    existing_keys: Set[str] = set()
    inserted = 0
    skipped = 0
    prepared_rows = []

    for match_id_str, match in matches.items():
        try:
            match_id = int(match_id_str)
        except ValueError:
            skipped += 1
            continue
        if match is None:
            skipped += 1
            continue

        # Filtrar solo partidos de los torneos que nos interesan
        tournament_id = match.get("tournamentId")
        if tournament_id not in TORNEOS_INTERES:
            skipped += 1
            continue

        # Filtrar partidos ya jugados o no disponibles
        if not match.get("available", False):
            skipped += 1
            continue
        if match.get("status") not in ("PREMATCH",):
            skipped += 1
            continue

        # Extraer equipos
        home_team = match.get("competitor1Name", "")
        away_team = match.get("competitor2Name", "")
        if not home_team or not away_team:
            skipped += 1
            continue

        partido = f"{home_team} vs {away_team}"
        competicion, deporte = TORNEOS_INTERES[tournament_id]

        # Fecha del partido
        match_start = match.get("matchStart")
        commence_time = None
        if match_start:
            try:
                commence_time = datetime.fromtimestamp(match_start, tz=timezone.utc)
            except Exception:
                pass

        # Extraer cuotas 1X2
        cuotas_1x2 = _extraer_cuotas_1x2(match_id, datos)
        if not cuotas_1x2:
            skipped += 1
            continue

        markets = {"1X2": cuotas_1x2}
        mercados = ["1X2"]

        dedupe_key = "||".join([
            "winamax",
            competicion.lower(),
            partido.lower(),
            "1x2",
            deporte.lower(),
        ])

        if dedupe_key in existing_keys:
            skipped += 1
            continue

        event = Event(
            bookie="winamax_fr",
            competicion=competicion,
            partido=partido,
            mercados=json.dumps(mercados, ensure_ascii=False),
            deporte=deporte,
            commence_time=commence_time,
            home_team=home_team,
            away_team=away_team,
            cuotas=json.dumps(markets, ensure_ascii=False),
            source="winamax_fr",
        )

        prepared_rows.append(event)
        existing_keys.add(dedupe_key)
        inserted += 1

    if prepared_rows:
        db.add_all(prepared_rows)
        db.commit()

        # Enviar datos al PC local
        try:
            import requests
            payload = []
            for e in prepared_rows:
                payload.append({
                    "bookie": e.bookie,
                    "competicion": e.competicion,
                    "partido": e.partido,
                    "mercados": e.mercados,
                    "deporte": e.deporte,
                    "commence_time": e.commence_time.isoformat() if e.commence_time else None,
                    "home_team": e.home_team,
                    "away_team": e.away_team,
                    "cuotas": e.cuotas,
                    "source": e.source,
                })
            r = requests.post(
                "http://88.12.220.235:8000/admin/push-winamax",
                json=payload,
                timeout=30
            )
            print(f"[Winamax] Datos enviados al PC local: {r.status_code}")
        except Exception as ex:
            print(f"[Winamax] Error enviando datos al PC local: {ex}")

    print(f"[Winamax] Insertados: {inserted}, Saltados: {skipped}")
    return {
        "provider": "winamax",
        "inserted": inserted,
        "skipped": skipped,
        "total_raw_matches": len(matches),
    }