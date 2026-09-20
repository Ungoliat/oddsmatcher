import json
import time
from typing import Any, Dict, List, Set
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from app.models.event import Event

# Competiciones de fútbol de Yosports que nos interesan.
# Yosports usa Kambi (un proveedor de apuestas de terceros muy extendido) y
# cada competición tiene una "ruta" (slug) legible, a diferencia de Sportium
# que usaba un ID numérico. La URL completa de cada una es:
# https://www.yosports.es/#sports-hub/football/{slug}
# (localizado navegando manualmente por el menú de ligas el 19/09/2026;
# si Yosports reorganiza su catálogo habría que revisar estos slugs).
COMPETICIONES: Dict[str, tuple] = {
    "spain/la_liga": ("LaLiga", "football"),
    "spain/la_liga_2": ("Segunda División", "football"),
    "england/premier_league": ("Premier League", "football"),
    "italy/serie_a": ("Serie A", "football"),
    "germany/bundesliga": ("Bundesliga", "football"),
    "france/ligue_1": ("Ligue 1", "football"),
    "champions_league": ("Champions League", "football"),
}

URL_BASE = "https://www.yosports.es/"
URL_COMPETICION = "https://www.yosports.es/#sports-hub/football/{slug}"

MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}

# Yosports abrevia el día de la semana en español para los partidos de los
# próximos ~6 días ("lun", "mar", "mié", "jue", "vie", "sáb", "dom") y a
# partir de ahí usa "DD mon" (p.ej. "13 oct"). No se ha visto que use
# "Hoy"/"Mañana" como Sportium, pero se contempla por si acaso.
DIAS_SEMANA = {
    "lun": 0, "mar": 1, "mié": 2, "mie": 2, "jue": 3,
    "vie": 4, "sáb": 5, "sab": 5, "dom": 6,
}


def _parsear_fecha(fecha_txt: str, hora_txt: str) -> datetime | None:
    """
    Convierte la fecha y hora que muestra Yosports (por separado, p.ej.
    fecha_txt='sáb' u fecha_txt='13 oct', hora_txt='21:00') a un datetime en
    UTC. Igual que en Sportium, es una conversión aproximada (asumimos que
    la hora ya está en hora de España); si falla, no rellenamos
    commence_time en vez de romper la sincronización completa.
    """
    if not fecha_txt or not hora_txt:
        return None

    fecha_txt = fecha_txt.strip().lower()
    hora_txt = hora_txt.strip()

    try:
        h, m = hora_txt.split(":")
        ahora = datetime.now(timezone.utc)

        if fecha_txt in ("hoy",):
            return ahora.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

        if fecha_txt in ("mañana", "manana"):
            fecha = ahora + timedelta(days=1)
            return fecha.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

        if fecha_txt in DIAS_SEMANA:
            objetivo = DIAS_SEMANA[fecha_txt]
            delta = (objetivo - ahora.weekday()) % 7
            fecha = ahora + timedelta(days=delta)
            return fecha.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

        # Formato "13 oct"
        dia_str, mes_str = fecha_txt.split(" ")
        mes_str = mes_str.strip(".")[:4]
        mes = MESES.get(mes_str, MESES.get(mes_str[:3]))
        if mes is None:
            return None

        fecha = datetime(ahora.year, mes, int(dia_str), int(h), int(m), tzinfo=timezone.utc)

        # Si con el año actual la fecha queda muy en el pasado, es que el
        # partido cae en el año que viene (p.ej. capturando en diciembre un
        # partido de enero).
        if fecha < ahora - timedelta(days=2):
            fecha = fecha.replace(year=ahora.year + 1)

        return fecha
    except Exception:
        return None


def _cerrar_banner_cookies(page) -> None:
    """Rechaza el banner de cookies si aparece. No es crítico si falla."""
    try:
        page.locator("button:has-text('Rechazar')").first.click(timeout=5000)
    except Exception:
        pass


def _extraer_partidos_de_pagina(page, nombre_comp: str, deporte: str) -> List[Dict[str, Any]]:
    """Lee los partidos ya renderizados en `page` (una página ya cargada en
    la competición `nombre_comp`) y los devuelve como lista de dicts."""
    partidos: List[Dict[str, Any]] = []

    filas = page.query_selector_all(".KambiBC-sandwich-filter__event-list-item")

    for fila in filas:
        try:
            participantes = fila.query_selector_all(".KambiBC-event-participants__name-participant-name")
            equipos = [p_el.inner_text().strip() for p_el in participantes]
            if len(equipos) != 2 or not equipos[0] or not equipos[1]:
                continue

            fecha_el = fila.query_selector(".KambiBC-event-item__start-time--date")
            hora_el = fila.query_selector(".KambiBC-event-item__start-time--time")
            fecha_txt = fecha_el.inner_text().strip() if fecha_el else None
            hora_txt = hora_el.inner_text().strip() if hora_el else None

            mercado_1x2 = fila.query_selector(".KambiBC-bet-offer--onecrosstwo")
            if not mercado_1x2:
                # Partido sin mercado 1X2 disponible (ya empezado, cancelado, etc.)
                continue

            outcomes = mercado_1x2.query_selector_all(".KambiBC-betty-outcome")
            cuotas_txt = [o.inner_text().strip() for o in outcomes]
            if len(cuotas_txt) != 3:
                continue

            cuota_1, cuota_x, cuota_2 = (
                float(c.replace(",", ".")) for c in cuotas_txt
            )

            link = fila.query_selector("a.KambiBC-sandwich-filter__event-list-info")
            href = link.get_attribute("href") if link else None
            event_id = href.rstrip("/").split("/")[-1] if href else None

            partidos.append({
                "event_id": event_id,
                "home_team": equipos[0],
                "away_team": equipos[1],
                "competicion": nombre_comp,
                "deporte": deporte,
                "fecha_txt": fecha_txt,
                "hora_txt": hora_txt,
                "cuota_1": cuota_1,
                "cuota_x": cuota_x,
                "cuota_2": cuota_2,
            })
        except Exception as e:
            print(f"[Yosports] Error procesando un partido de {nombre_comp}: {e}")
            continue

    return partidos


def _capturar_datos_yosports() -> List[Dict[str, Any]]:
    """
    Recorre cada competición de interés en Yosports y extrae, para cada
    partido con mercado 1X2 disponible: equipos, fecha/hora, id del evento
    y las tres cuotas (local/empate/visitante).

    Yosports usa Kambi (un proveedor de apuestas de terceros muy usado en
    España). A diferencia de Sportium (que usa IDs numéricos y una pestaña
    nueva por competición porque su widget se rompía si se reutilizaba una
    sola pestaña), en Yosports cada competición tiene una URL con nombre
    legible (p.ej. "#sports-hub/football/spain/la_liga") y la app se
    comporta bien navegando de una a otra dentro de la MISMA pestaña,
    SIEMPRE que la pestaña haya cargado antes la página base
    (https://www.yosports.es/) sin ningún "#" al final: si se intenta
    cargar directamente una URL con "#sports-hub/..." como primera carga de
    la pestaña, la aplicación no la reconoce y redirige a la portada. Por
    eso primero cargamos la home a secas y luego, ya con la app arrancada,
    vamos cambiando de competición con la URL completa.
    """
    from playwright.sync_api import sync_playwright

    eventos: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="es-ES",
        )

        # Primera carga: la home a secas, para que la app arranque bien.
        try:
            page.goto(URL_BASE, wait_until="domcontentloaded", timeout=30000)
            _cerrar_banner_cookies(page)
            time.sleep(2)
        except Exception as e:
            print(f"[Yosports] Error cargando la home: {e}")

        for slug, (nombre_comp, deporte) in COMPETICIONES.items():
            url = URL_COMPETICION.format(slug=slug)
            print(f"[Yosports] Capturando {nombre_comp}...")

            partidos_comp: List[Dict[str, Any]] = []
            for intento in (1, 2):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    # El widget de Kambi puede tardar varios segundos en
                    # pintar la lista de partidos (más si hay muchas
                    # "apuestas especiales" antes en la página), así que
                    # esperamos al selector en vez de un sleep fijo.
                    page.wait_for_selector(
                        ".KambiBC-sandwich-filter__event-list-item",
                        timeout=20000,
                    )
                    time.sleep(1)

                    partidos_comp = _extraer_partidos_de_pagina(page, nombre_comp, deporte)

                    if partidos_comp:
                        break
                    if intento == 1:
                        print(f"[Yosports] {nombre_comp}: 0 partidos en el primer intento, reintentando...")
                except Exception as e:
                    print(f"[Yosports] Error en {nombre_comp} (intento {intento}): {e}")
                    if intento == 1:
                        # Por si la app se quedó en un estado raro, recargamos
                        # la home antes de reintentar.
                        try:
                            page.goto(URL_BASE, wait_until="domcontentloaded", timeout=30000)
                            time.sleep(2)
                        except Exception:
                            pass

            eventos.extend(partidos_comp)
            print(f"[Yosports] {nombre_comp}: {len(partidos_comp)} partidos encontrados")

            time.sleep(1.5)

        browser.close()

    return eventos


def sync_events_from_yosports(db: Session) -> Dict[str, Any]:
    """
    Sincroniza eventos de Yosports en la base de datos, igual que hacen
    sync_events_from_sportium() y sync_events_from_winamax().
    """
    print("[Yosports] Iniciando captura de datos via Playwright...")
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

        commence_time = _parsear_fecha(ev["fecha_txt"], ev["hora_txt"])

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
            external_id=ev["event_id"],
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
