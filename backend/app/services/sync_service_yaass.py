"""
Scraper de Yaass Casino (yaasscasino.es) — vía la API de Orenes.

A DIFERENCIA de todos los demás scrapers del proyecto (Winamax, Sportium,
Yosports, Marcaapuestas, Versus...), este NO abre ningún navegador. Yaass
usa por detrás una plataforma de terceros llamada "Orenes"
(online-sportsbook.orenes.tech) que expone sus datos mediante una API de
tipo GraphQL. Se confirmó (probando directamente desde fuera del navegador)
que esa API no tiene la protección anti-robots (Cloudflare) que sí protege
la página visual — solo hace falta una cabecera fija (x-api-key) y el
identificador de Yaass dentro de esa plataforma (tenantId). Por eso este
archivo usa la librería `requests` en vez de Playwright, y no necesita
`_browser_scraper_lock` (no compite por ningún navegador).

Todo esto se investigó y confirmó el 26-27/09/2026 capturando el tráfico
de red mientras se navegaba a mano (para saltarse el bloqueo de Cloudflare
en la pantalla) y, después, preguntándole a la propia API su "mapa" de
datos disponibles (función estándar de GraphQL llamada "introspection").
El detalle completo está en el documento del proyecto
"versus_yaass_investigacion.md".
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import requests
from sqlalchemy.orm import Session

from app.models.event import Event

ORENES_URL = "https://online-sportsbook.orenes.tech/offermanager/graphql"

# Identificador de Yaass dentro de la plataforma Orenes (que probablemente
# sirve también a otras casas del mismo grupo RFranco, cada una con el suyo).
TENANT_ID = "bb4500d9-53c7-4496-9345-af294bec5afd"

# Cabecera "de aplicación" fija que exige la API — igual para todo el mundo
# que use esta web, no es una clave personal de Andrew.
X_API_KEY = "xEuh64cHUBr3v88mEd0tsLa4fU"

# 1 = Fútbol dentro del catálogo de deportes de Orenes (confirmado con datos
# reales: los partidos de fútbol vienen siempre con "sportKey": 1).
SPORT_KEY_FUTBOL = 1

# Los "códigos" (tournamentId) de las 7 ligas habituales del proyecto DENTRO
# de la plataforma Orenes — no tienen nada que ver con los IDs usados en
# Sportium/Marcaapuestas/Versus (esos son de Playtech, un sistema distinto).
# Confirmados uno a uno el 27/09/2026 pidiéndole a la propia API la lista
# completa de competiciones de fútbol y comprobando cuál de los candidatos
# con el mismo nombre tenía partidos reales programados (algunas ligas
# tienen un segundo código "especial", tipo apuesta a "quién gana la Liga",
# que no tiene partidos individuales — esos se descartaron).
TORNEOS: Dict[str, str] = {
    "18805502-fb1e-4f91-9a42-8b9474917b5d": "LaLiga",
    "632a70d2-d0fd-43b0-9a09-ceae1bbf0bd8": "Segunda División",
    "1df912e5-6860-4c46-bdb9-6da70188693b": "Premier League",
    "b95f05c2-a28c-4d06-b740-7721b61fdef1": "Serie A",
    "9e050aa8-7d4a-4c51-846b-6158bea7b438": "Bundesliga",
    "d5b09982-cc55-4a8a-9b78-d5b72b181ec7": "Ligue 1",
    "a78774ba-a65e-47d5-a654-abde7edb2187": "Champions League",
}

# Códigos de mercado (marketKey) confirmados con datos reales — mucho más
# fiables que buscar por el texto del nombre (que podría escribirse
# distinto o cambiar de idioma).
MARKET_KEY_1X2 = 1
MARKET_KEY_VENTAJA_2_GOLES = 361

HEADERS = {
    "accept": "*/*",
    "accept-language": "es",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": "https://online-sportsbook.orenes.tech",
    "pragma": "no-cache",
    "referer": "https://online-sportsbook.orenes.tech/",
    "x-api-key": X_API_KEY,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}

# Pedimos, en la misma pregunta, la lista de partidos de las 7 ligas Y sus
# mercados (usando "... on Fixture" para entrar en los datos propios de un
# partido de verdad, igual que se hace en la web). Así una sola llamada
# (con sus tandas de 100 en 100, ver más abajo) trae todo lo necesario, sin
# tener que preguntar partido por partido.
QUERY = """
query eventsPorLigas($filter: FilterInput!, $after: String) {
  events(filter: $filter, first: 100, after: $after) {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        eventId
        eventName
        utcStartDate
        offerActive
        hasEnded
        tournament {
          tournamentId
          tournamentName
        }
        ... on Fixture {
          marketHeaders(isActive: true, onlyMainMarkets: false) {
            marketKey
            markets {
              marketKey
              marketName
              active
              marketTags
              selectionHeaders {
                selectionKey
                selectionName
                selections {
                  price
                  selectionName
                  offerStatus
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def _parsear_fecha(iso_txt: Optional[str]):
    """Convierte la fecha que da Orenes ('2026-10-09T19:00:00.000Z') a un
    datetime en UTC. Si algo falla, devolvemos None en vez de romper toda
    la sincronización por un solo partido con fecha rara."""
    if not iso_txt:
        return None
    try:
        return datetime.fromisoformat(iso_txt.replace("Z", "+00:00"))
    except Exception:
        return None


def _extraer_cuotas_de_mercado(market: Dict[str, Any]) -> Dict[str, float]:
    """Convierte el bloque 'selectionHeaders' de un mercado en un diccionario
    simple {nombre_seleccion: cuota}, igual que usan el resto de scrapers
    del proyecto para que el emparejamiento con Betfair funcione igual.

    El nombre real de cada selección (el equipo, o 'X' para el empate) no
    está en 'selectionName' de la cabecera, sino dentro de la primera
    (y única) 'selection' de cada cabecera — así viene en la respuesta real
    de Orenes. Aquí normalizamos 'X' a 'draw', igual que hacen los demás
    scrapers del proyecto con el empate.
    """
    cuotas: Dict[str, float] = {}
    for header in market.get("selectionHeaders") or []:
        selections = header.get("selections") or []
        if not selections:
            continue
        sel = selections[0]
        nombre = sel.get("selectionName")
        precio = sel.get("price")
        if not nombre or precio is None:
            continue
        if sel.get("offerStatus") and sel["offerStatus"] != "Active":
            continue
        clave = "draw" if nombre.strip().upper() == "X" else nombre.strip()
        cuotas[clave] = precio
    return cuotas


def _pedir_pagina(filtro: Dict[str, Any], after: Optional[str]) -> Dict[str, Any]:
    """Pide una tanda (hasta 100 partidos) a la API de Orenes. Yaass limita
    cada pregunta a 100 resultados como máximo, así que para más de 100
    partidos entre las 7 ligas hace falta pedir varias tandas seguidas
    (ver el bucle en _capturar_datos_yaass)."""
    variables = {"filter": filtro, "after": after}
    resp = requests.post(
        ORENES_URL,
        json={"query": QUERY, "variables": variables},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"Orenes devolvió errores: {data['errors']}")
    return data["data"]["events"]


def _capturar_datos_yaass() -> List[Dict[str, Any]]:
    """Trae todos los partidos de las 7 ligas de interés, con sus mercados
    ya incluidos, pidiendo tantas tandas de 100 como hagan falta."""
    filtro = {
        "tenantId": TENANT_ID,
        "tournamentsId": list(TORNEOS.keys()),
        "sportKeys": [SPORT_KEY_FUTBOL],
        "ended": False,
    }

    eventos: List[Dict[str, Any]] = []
    after = None
    tanda = 1

    while True:
        pagina = _pedir_pagina(filtro, after)
        for edge in pagina.get("edges") or []:
            eventos.append(edge["node"])

        page_info = pagina.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
        tanda += 1
        if tanda > 50:  # margen de seguridad, no debería hacer falta nunca
            print("[Yaass] Aviso: se paró tras 50 tandas (5000 partidos) por seguridad")
            break

    return eventos


def sync_events_from_yaass(db: Session) -> Dict[str, Any]:
    """
    Sincroniza eventos de Yaass Casino en la base de datos, con el mismo
    formato que usan el resto de sincronizaciones del proyecto
    (sync_events_from_sportium, sync_events_from_winamax, etc.).

    A diferencia de esas, esta NO necesita el candado _browser_scraper_lock
    de main.py: no abre ningún navegador, así que puede ejecutarse a la vez
    que cualquier otra sincronización sin ningún problema.
    """
    print("[Yaass] Iniciando captura de datos vía API directa (sin navegador)...")

    try:
        eventos_raw = _capturar_datos_yaass()
    except Exception as e:
        return {
            "provider": "yaass",
            "inserted": 0,
            "skipped": 0,
            "error": f"No se pudo contactar con la API de Yaass/Orenes: {e}",
        }

    if not eventos_raw:
        return {
            "provider": "yaass",
            "inserted": 0,
            "skipped": 0,
            "error": "No se capturaron datos de Yaass",
        }

    print(f"[Yaass] Datos capturados: {len(eventos_raw)} partidos")

    existing_keys: Set[str] = set()
    inserted = 0
    skipped = 0
    prepared_rows = []

    for ev in eventos_raw:
        if not ev.get("offerActive") or ev.get("hasEnded"):
            skipped += 1
            continue

        nombre_evento = ev.get("eventName") or ""
        if " - " not in nombre_evento:
            # Formato inesperado (no son los dos equipos separados por
            # ' - '); nos lo saltamos en vez de arriesgarnos a guardar
            # datos mal cortados.
            skipped += 1
            continue

        home_team, away_team = nombre_evento.split(" - ", 1)
        home_team = home_team.strip()
        away_team = away_team.strip()

        tournament = ev.get("tournament") or {}
        competicion = TORNEOS.get(tournament.get("tournamentId"), tournament.get("tournamentName") or "Desconocida")

        partido = f"{home_team} vs {away_team}"
        commence_time = _parsear_fecha(ev.get("utcStartDate"))

        # Buscamos, entre todos los mercados que trajo el partido, el 1X2
        # normal (marketKey 1) y "Ganador por ventaja (2 goles)"
        # (marketKey 361) — usando el código numérico, no el texto, porque
        # es mucho más fiable (ver el documento de investigación del
        # proyecto para el porqué).
        markets: Dict[str, Dict[str, float]] = {}
        for header in ev.get("marketHeaders") or []:
            for market in header.get("markets") or []:
                if not market.get("active"):
                    continue
                key = market.get("marketKey")
                if key == MARKET_KEY_1X2:
                    cuotas = _extraer_cuotas_de_mercado(market)
                    if cuotas:
                        markets["1X2"] = cuotas
                elif key == MARKET_KEY_VENTAJA_2_GOLES:
                    cuotas = _extraer_cuotas_de_mercado(market)
                    if cuotas:
                        # Aquí SÍ son cuotas distintas a las del 1X2 normal
                        # (a diferencia de Sportium/Marcaapuestas/Versus,
                        # donde este nombre de mercado guarda las mismas
                        # cuotas que el 1X2 porque es solo una condición de
                        # pago anticipado, no un mercado aparte).
                        markets["1X2_Ventaja2Goles"] = cuotas

        if not markets.get("1X2"):
            # Sin ni siquiera el 1X2 normal, este partido no sirve de nada
            # para el resto de la aplicación.
            skipped += 1
            continue

        dedupe_key = "||".join([
            "yaass",
            competicion.lower(),
            partido.lower(),
        ])
        if dedupe_key in existing_keys:
            skipped += 1
            continue

        event = Event(
            bookie="yaass",
            competicion=competicion,
            partido=partido,
            mercados=json.dumps(list(markets.keys()), ensure_ascii=False),
            deporte="football",
            commence_time=commence_time,
            home_team=home_team,
            away_team=away_team,
            cuotas=json.dumps(markets, ensure_ascii=False),
            source="yaass",
            external_id=ev.get("eventId"),
        )

        prepared_rows.append(event)
        existing_keys.add(dedupe_key)
        inserted += 1

    if prepared_rows:
        db.query(Event).filter(Event.source == "yaass").delete()
        db.add_all(prepared_rows)
        db.commit()
    else:
        print("[Yaass] Ningún partido válido en esta pasada; se mantienen los datos de Yaass de la sincronización anterior.")

    print(f"[Yaass] Insertados: {inserted}, Saltados: {skipped}")
    return {
        "provider": "yaass",
        "inserted": inserted,
        "skipped": skipped,
        "total_raw_matches": len(eventos_raw),
    }
