import json
import time
from typing import Any, Dict, List, Set
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from app.models.event import Event

# Competiciones de fútbol de Sportium que nos interesan.
# El ID es el "competitionId" que usa Sportium en su URL:
# https://www.sportium.es/apuestas/sports/soccer/competitions/{ID}/matches
# (localizado inspeccionando manualmente el menú de competiciones el 10/09/2026;
# si Sportium cambia sus IDs internos habría que volver a capturarlos igual).
COMPETICIONES: Dict[int, tuple] = {
    45211: ("LaLiga", "football"),
    45215: ("Segunda División", "football"),
    40527: ("Premier League", "football"),
    44571: ("Serie A", "football"),
    45915: ("Bundesliga", "football"),
    46074: ("Ligue 1", "football"),
    45225: ("Champions League", "football"),
}

URL_COMPETICION = "https://www.sportium.es/apuestas/sports/soccer/competitions/{competition_id}/matches"

MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}


def _parsear_fecha(texto: str) -> datetime | None:
    """
    Convierte las fechas relativas que muestra Sportium en la lista de partidos
    ('Hoy, 18:45' / 'Mañana, 21:00' / '12 sept, 14:00') a un datetime en UTC.

    Es una conversión aproximada (asumimos que la hora mostrada ya está en
    hora de España); si algún día falla, simplemente no rellenamos
    commence_time en vez de romper la sincronización completa.
    """
    if not texto:
        return None

    texto = texto.strip().lower()
    ahora = datetime.now(timezone.utc)

    try:
        if texto.startswith("hoy"):
            hora_str = texto.split(",")[1].strip()
            h, m = hora_str.split(":")
            return ahora.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

        if texto.startswith("mañana") or texto.startswith("manana"):
            hora_str = texto.split(",")[1].strip()
            h, m = hora_str.split(":")
            fecha = ahora + timedelta(days=1)
            return fecha.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

        # Formato "12 sept, 14:00"
        fecha_part, hora_part = texto.split(",")
        dia_str, mes_str = fecha_part.strip().split(" ")
        mes_str = mes_str.strip(".")[:4]
        mes = MESES.get(mes_str, MESES.get(mes_str[:3]))
        if mes is None:
            return None

        h, m = hora_part.strip().split(":")
        fecha = datetime(ahora.year, mes, int(dia_str), int(h), int(m), tzinfo=timezone.utc)

        # Si al construir la fecha con el año actual queda muy en el pasado,
        # es que el partido cae ya en el año que viene (p.ej. capturando en
        # diciembre un partido de enero).
        if fecha < ahora - timedelta(days=2):
            fecha = fecha.replace(year=ahora.year + 1)

        return fecha
    except Exception:
        return None


def _cerrar_banner_cookies(page) -> None:
    """Rechaza el banner de cookies (Cookiebot) si aparece. No es crítico si falla."""
    try:
        page.locator("button:has-text('Rechazar')").first.click(timeout=5000)
    except Exception:
        pass


def _capturar_datos_sportium() -> List[Dict[str, Any]]:
    """
    Recorre cada competición de interés en Sportium y extrae, para cada
    partido con mercado 1X2 disponible: equipos, fecha/hora, id del evento
    y las tres cuotas (local/empate/visitante).

    A diferencia de Winamax (que expone las cuotas por WebSocket), en
    Sportium las cuotas se leen directamente del HTML ya renderizado:
    cada partido es un bloque `.ta-EventListItem` y las cuotas 1X2 están en
    `.ta-MarketType-MRES .ta-price_text` dentro de ese bloque, en el orden
    1 / X / 2.
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

        cookies_cerradas = False

        for competition_id, (nombre_comp, deporte) in COMPETICIONES.items():
            url = URL_COMPETICION.format(competition_id=competition_id)
            print(f"[Sportium] Capturando {nombre_comp}...")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                if not cookies_cerradas:
                    _cerrar_banner_cookies(page)
                    cookies_cerradas = True

                page.wait_for_selector(".ta-EventListItem", timeout=15000)
                # Pequeño margen para que terminen de pintarse todas las cuotas
                time.sleep(1.5)

                filas = page.query_selector_all(".ta-EventListItem")

                for fila in filas:
                    try:
                        fecha_el = fila.query_selector('div[style*="font-size: 12px"]')
                        fecha_txt = fecha_el.inner_text().strip() if fecha_el else None

                        participantes = fila.query_selector_all(".ta-ParticipantItem")
                        equipos = [p_el.inner_text().strip() for p_el in participantes]
                        if len(equipos) != 2 or not equipos[0] or not equipos[1]:
                            continue

                        link = fila.query_selector('a[href*="/events/"]')
                        event_id = link.get_attribute("href").rstrip("/").split("/")[-1] if link else None

                        precios = fila.query_selector_all(".ta-MarketType-MRES .ta-price_text")
                        cuotas_txt = [pr.inner_text().strip() for pr in precios]
                        if len(cuotas_txt) != 3:
                            # Partido sin mercado 1X2 disponible (ya empezado, cancelado, etc.)
                            continue

                        cuota_1, cuota_x, cuota_2 = (
                            float(c.replace(",", ".")) for c in cuotas_txt
                        )

                        eventos.append({
                            "event_id": event_id,
                            "home_team": equipos[0],
                            "away_team": equipos[1],
                            "competicion": nombre_comp,
                            "deporte": deporte,
                            "fecha_txt": fecha_txt,
                            "cuota_1": cuota_1,
                            "cuota_x": cuota_x,
                            "cuota_2": cuota_2,
                        })
                    except Exception as e:
                        print(f"[Sportium] Error procesando un partido de {nombre_comp}: {e}")
                        continue

                print(f"[Sportium] {nombre_comp}: {len(filas)} partidos encontrados")

            except Exception as e:
                print(f"[Sportium] Error en {nombre_comp}: {e}")
                continue

            # Pausa entre competiciones para no saturar el sitio
            time.sleep(2)

        browser.close()

    return eventos


def sync_events_from_sportium(db: Session) -> Dict[str, Any]:
    """
    Sincroniza eventos de Sportium en la base de datos, igual que hace
    sync_events_from_winamax() para Winamax.
    """
    print("[Sportium] Iniciando captura de datos via Playwright...")
    eventos_raw = _capturar_datos_sportium()

    if not eventos_raw:
        return {
            "provider": "sportium",
            "inserted": 0,
            "skipped": 0,
            "error": "No se capturaron datos de Sportium",
        }

    print(f"[Sportium] Datos capturados: {len(eventos_raw)} partidos")

    # Borrar eventos anteriores de Sportium antes de insertar los nuevos
    db.query(Event).filter(Event.source == "sportium").delete()
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

        commence_time = _parsear_fecha(ev["fecha_txt"])

        # Mismo formato que usan el resto de providers (the_odds_api, oddspapi):
        # las claves home/away son el nombre literal del equipo tal cual lo
        # da la casa, y "draw" para el empate. Así el emparejamiento fuzzy con
        # Betfair (sync_service_betfair.py) funciona igual que con Winamax.
        markets = {
            "1X2": {
                home_team: ev["cuota_1"],
                "draw": ev["cuota_x"],
                away_team: ev["cuota_2"],
            }
        }

        dedupe_key = "||".join([
            "sportium",
            competicion.lower(),
            partido.lower(),
            "1x2",
        ])

        if dedupe_key in existing_keys:
            skipped += 1
            continue

        event = Event(
            bookie="sportium",
            competicion=competicion,
            partido=partido,
            mercados=json.dumps(["1X2"], ensure_ascii=False),
            deporte=ev["deporte"],
            commence_time=commence_time,
            home_team=home_team,
            away_team=away_team,
            cuotas=json.dumps(markets, ensure_ascii=False),
            source="sportium",
            external_id=ev["event_id"],
        )

        prepared_rows.append(event)
        existing_keys.add(dedupe_key)
        inserted += 1

    if prepared_rows:
        db.add_all(prepared_rows)
        db.commit()

    print(f"[Sportium] Insertados: {inserted}, Saltados: {skipped}")
    return {
        "provider": "sportium",
        "inserted": inserted,
        "skipped": skipped,
        "total_raw_matches": len(eventos_raw),
    }
