import json
from typing import Any, Dict, List, Set
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session
from app.models.event import Event

# ---------------------------------------------------------------------------
# REESCRITO EL 21/09/2026 — cambio de enfoque completo
# ---------------------------------------------------------------------------
# Las versiones anteriores de este scraper abrían un navegador (Playwright)
# y "leían" la web de Yosports como lo haría una persona. Después de varias
# rondas de pruebas (headless, con ventana, esperando más tiempo...) se
# descubrió, inspeccionando el tráfico de red de la propia web con la
# extensión de Claude en Chrome, que la web de Yosports en realidad obtiene
# los partidos y las cuotas llamando a una API pública en JSON del propio
# proveedor de apuestas que usa por debajo (Kambi):
#
#   https://eu.offering-api.kambicdn.com/offering/v2018/yosportses/listView/
#       football/<país>/<liga>.json?lang=es_ES&market=ES&client_id=200&channel_id=1
#
# Esta API es la misma que usa el navegador del usuario para pintar la
# tabla de partidos, así que en vez de simular un navegador entero (con
# todos los problemas de arranque, tiempos de carga y demás que se han
# visto) simplemente le pedimos los datos directamente por HTTP, como se
# hace ya con Winamax (que usa WebSocket) en vez de leer su HTML.
#
# Ventajas de este cambio:
# - Mucho más rápido (unas pocas peticiones JSON en vez de abrir un
#   navegador completo).
# - No depende de que la aplicación de Yosports termine de "arrancar" a
#   tiempo, ni de si el navegador es visible o no.
# - La fecha de cada partido viene ya en un formato estándar (ISO 8601),
#   así que no hace falta interpretar textos como "sáb" o "13 oct".
#
# Si en el futuro Yosports cambia de proveedor de cuotas (deja de usar
# Kambi) o cambia esta API, habría que volver a inspeccionar el tráfico de
# red de la web (con las herramientas de desarrollador del navegador, o con
# la extensión de Claude en Chrome) para encontrar la nueva URL.
# ---------------------------------------------------------------------------

# Mismos slugs que se usaban para las URLs de la web (localizados navegando
# manualmente por el menú de ligas el 19/09/2026); aquí se usan para
# construir la URL de la API en vez de la URL de la página.
COMPETICIONES: Dict[str, tuple] = {
    "spain/la_liga": ("LaLiga", "football"),
    "spain/la_liga_2": ("Segunda División", "football"),
    "england/premier_league": ("Premier League", "football"),
    "italy/serie_a": ("Serie A", "football"),
    "germany/bundesliga": ("Bundesliga", "football"),
    "france/ligue_1": ("Ligue 1", "football"),
    "champions_league": ("Champions League", "football"),
}

URL_API = (
    "https://eu.offering-api.kambicdn.com/offering/v2018/yosportses/listView/"
    "football/{slug}.json?lang=es_ES&market=ES&client_id=200&channel_id=1"
)

HEADERS = {
    # Un user-agent y un "Referer" normales, como los que mandaría el
    # navegador al cargar la web — esta API es pública (la usa el propio
    # sitio desde el navegador de cualquier visitante), pero por si acaso
    # comprobara de dónde viene la petición, se lo indicamos igualmente.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.yosports.es/",
    "Accept": "application/json",
}


def _extraer_1x2(bet_offers: List[Dict[str, Any]]):
    """Busca, dentro de los mercados ("betOffers") que trae la API para un
    partido, el mercado de resultado final (1X2) y devuelve las tres
    cuotas ya convertidas a decimal (la API las da como enteros x1000,
    p.ej. 2400 significa 2.40). Devuelve None si no lo encuentra."""
    for oferta in bet_offers or []:
        criterio = oferta.get("criterion") or {}
        if criterio.get("occurrenceType") != "GOALS" or criterio.get("lifetime") != "FULL_TIME":
            continue

        cuota_1 = cuota_x = cuota_2 = None
        for outcome in oferta.get("outcomes", []):
            tipo = outcome.get("type")
            odds = outcome.get("odds")
            if odds is None:
                continue
            valor = odds / 1000
            if tipo == "OT_ONE":
                cuota_1 = valor
            elif tipo == "OT_CROSS":
                cuota_x = valor
            elif tipo == "OT_TWO":
                cuota_2 = valor

        if cuota_1 is not None and cuota_x is not None and cuota_2 is not None:
            return cuota_1, cuota_x, cuota_2

    return None


def _capturar_datos_yosports() -> List[Dict[str, Any]]:
    """Pide a la API de Kambi la lista de partidos (con sus cuotas 1X2 ya
    incluidas) de cada competición de interés. Reintenta una vez por
    competición si la petición falla o no llega ninguna respuesta válida."""
    eventos: List[Dict[str, Any]] = []

    for slug, (nombre_comp, deporte) in COMPETICIONES.items():
        url = URL_API.format(slug=slug)
        print(f"[Yosports] Consultando {nombre_comp}...")

        partidos_comp: List[Dict[str, Any]] = []
        for intento in (1, 2):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    print(f"[Yosports] {nombre_comp} (intento {intento}): HTTP {resp.status_code}")
                    continue

                datos = resp.json()
                for item in datos.get("events", []):
                    evento = item.get("event", {})
                    cuotas = _extraer_1x2(item.get("betOffers"))
                    if cuotas is None:
                        # Partido sin mercado 1X2 disponible todavía (o ya
                        # empezado / cancelado).
                        continue

                    home_team = evento.get("homeName")
                    away_team = evento.get("awayName")
                    if not home_team or not away_team:
                        continue

                    cuota_1, cuota_x, cuota_2 = cuotas
                    partidos_comp.append({
                        "event_id": evento.get("id"),
                        "home_team": home_team,
                        "away_team": away_team,
                        "competicion": nombre_comp,
                        "deporte": deporte,
                        "start_iso": evento.get("start"),
                        "cuota_1": cuota_1,
                        "cuota_x": cuota_x,
                        "cuota_2": cuota_2,
                    })

                break  # si hemos llegado hasta aquí, la petición ha ido bien
            except Exception as e:
                print(f"[Yosports] Error en {nombre_comp} (intento {intento}): {e}")

        eventos.extend(partidos_comp)
        print(f"[Yosports] {nombre_comp}: {len(partidos_comp)} partidos encontrados")

    return eventos


def sync_events_from_yosports(db: Session) -> Dict[str, Any]:
    """
    Sincroniza eventos de Yosports en la base de datos, igual que hacen
    sync_events_from_sportium() y sync_events_from_winamax().
    """
    print("[Yosports] Iniciando captura de datos via la API de Kambi...")
    eventos_raw = _capturar_datos_yosports()

    if not eventos_raw:
        return {
            "provider": "yosports",
            "inserted": 0,
            "skipped": 0,
            "error": "No se capturaron datos de Yosports",
        }

    print(f"[Yosports] Datos capturados: {len(eventos_raw)} partidos")

    # Borrar eventos anteriores de Yosports antes de insertar los nuevos
    db.query(Event).filter(Event.source == "yosports").delete()
    db.commit()

    existing_keys: Set[str] = set()
    inserted = 0
    skipped = 0
    prepared_rows = []

    for ev in eventos_raw:
        home_team = ev["home_team"]
        away_team = ev["away_team"]
        partido = f"{home_team} vs {away_team}"
        competicion = ev["competicion"]

        commence_time = None
        if ev.get("start_iso"):
            try:
                # La API da la fecha en ISO 8601 UTC (p.ej.
                # "2026-10-09T19:00:00Z"), mucho más fiable que interpretar
                # textos como "sáb" o "13 oct" a partir del HTML.
                commence_time = datetime.fromisoformat(
                    ev["start_iso"].replace("Z", "+00:00")
                )
            except Exception:
                commence_time = None

        # Mismo formato que el resto de providers: las claves home/away son
        # el nombre literal del equipo tal cual lo da la casa, y "draw"
        # para el empate. Así el emparejamiento fuzzy con Betfair
        # (sync_service_betfair.py) funciona igual que con Winamax/Sportium.
        markets = {
            "1X2": {
                home_team: ev["cuota_1"],
                "draw": ev["cuota_x"],
                away_team: ev["cuota_2"],
            }
        }

        dedupe_key = "||".join([
            "yosports",
            competicion.lower(),
            partido.lower(),
            "1x2",
        ])

        if dedupe_key in existing_keys:
            skipped += 1
            continue

        event = Event(
            bookie="yosports",
            competicion=competicion,
            partido=partido,
            mercados=json.dumps(["1X2"], ensure_ascii=False),
            deporte=ev["deporte"],
            commence_time=commence_time,
            home_team=home_team,
            away_team=away_team,
            cuotas=json.dumps(markets, ensure_ascii=False),
            source="yosports",
            external_id=str(ev["event_id"]) if ev.get("event_id") is not None else None,
        )

        prepared_rows.append(event)
        existing_keys.add(dedupe_key)
        inserted += 1

    if prepared_rows:
        db.add_all(prepared_rows)
        db.commit()

    print(f"[Yosports] Insertados: {inserted}, Saltados: {skipped}")
    return {
        "provider": "yosports",
        "inserted": inserted,
        "skipped": skipped,
        "total_raw_matches": len(eventos_raw),
    }
