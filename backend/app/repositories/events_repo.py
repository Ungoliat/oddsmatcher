import json
from sqlalchemy.orm import Session
from thefuzz import fuzz

from app.models.event import Event
from app.core.normalizer import normalizar_partido


def replace_events(db: Session, events: list[dict]):
    db.query(Event).delete()

    for item in events:
        event = Event(
            bookie=item["bookie"],
            competicion=item["competicion"],
            partido=item["partido"],
            deporte=item["deporte"],
            mercados=json.dumps(item["mercados"], ensure_ascii=False),
        )
        db.add(event)

    db.commit()


def get_events(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    deporte: str | None = None,
    bookie: str | None = None,
    mercado: str | None = None,
    competicion: str | None = None,
    partido: str | None = None,
):
    query = db.query(Event)

    if deporte:
        query = query.filter(Event.deporte == deporte)

    if bookie:
        query = query.filter(Event.bookie == bookie)

    if mercado:
        query = query.filter(Event.mercados.like(f"%{mercado}%"))

    if competicion:
        query = query.filter(Event.competicion.ilike(f"%{competicion.strip()}%"))

    if partido:
        query = query.filter(Event.partido.ilike(f"%{partido.strip()}%"))

    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    events = []
    for row in rows:
        try:
            mercados = json.loads(row.mercados)
        except Exception:
            mercados = []

        events.append({
            "id": row.id,
            "bookie": row.bookie,
            "competicion": row.competicion,
            "partido": row.partido,
            "deporte": row.deporte,
            "mercados": mercados,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": events,
    }


def get_grouped_events(
    db: Session,
    deporte: str | None = None,
    competicion: str | None = None,
    partido: str | None = None,
    bookie: str | None = None,
    umbral_fuzzy: int = 85,
):
    query = db.query(Event)

    if deporte:
        query = query.filter(Event.deporte == deporte)

    if bookie:
        query = query.filter(Event.bookie == bookie)

    if competicion:
        query = query.filter(Event.competicion.ilike(f"%{competicion.strip()}%"))

    if partido:
        query = query.filter(Event.partido.ilike(f"%{partido.strip()}%"))

    rows = query.order_by(
        Event.deporte.asc(),
        Event.competicion.asc(),
        Event.partido.asc(),
        Event.bookie.asc(),
    ).all()

    # ------------------------------------------------------------------
    # Antes, esta función agrupaba comparando el texto de "partido" tal
    # cual lo guarda cada casa (letra por letra). El problema es que cada
    # casa escribe los nombres de los equipos de forma distinta ("Real
    # Madrid vs FC Barcelona" en Winamax frente a "R. Madrid vs Barcelona"
    # en Sportium), así que nunca coincidían y cada casa acababa en su
    # propio grupo, sin cruzarse nunca entre sí — que es justo lo que hace
    # falta para el Dutcher 3B.
    #
    # Ahora reutilizamos el mismo "traductor de nombres" (normalizar_partido)
    # que ya se usaba para emparejar con Betfair, y si dos partidos de la
    # misma liga tienen un nombre normalizado igual o muy parecido (fuzzy
    # matching), se juntan en el mismo grupo. Los datos que se devuelven
    # siguen mostrando el nombre "original" tal cual lo escribió la primera
    # casa que se proceso, para que la pantalla no se vea rara.
    # ------------------------------------------------------------------
    grupos_por_liga: dict[tuple, list[dict]] = {}

    for row in rows:
        bucket_key = (row.deporte, row.competicion)
        partido_normalizado = normalizar_partido(row.partido)

        try:
            mercados = json.loads(row.mercados)
            if not isinstance(mercados, list):
                mercados = []
        except Exception:
            mercados = []

        try:
            cuotas = json.loads(row.cuotas) if row.cuotas else {}
        except Exception:
            cuotas = {}

        entrada_bookie = {
            "bookie": row.bookie,
            "mercados": sorted(set(mercados)),
            "cuotas": cuotas,
        }

        bucket = grupos_por_liga.setdefault(bucket_key, [])

        # 1) ¿Ya hay un grupo con el mismo nombre normalizado exacto?
        grupo_encontrado = None
        for grupo in bucket:
            if grupo["_partido_normalizado"] == partido_normalizado:
                grupo_encontrado = grupo
                break

        # 2) Si no, ¿hay uno muy parecido (fuzzy matching), dentro de la
        #    misma liga/deporte, para no mezclar partidos de ligas distintas?
        if grupo_encontrado is None:
            for grupo in bucket:
                ratio = fuzz.token_sort_ratio(
                    grupo["_partido_normalizado"], partido_normalizado
                )
                if ratio >= umbral_fuzzy:
                    grupo_encontrado = grupo
                    break

        if grupo_encontrado is None:
            grupo_encontrado = {
                "deporte": row.deporte,
                "competicion": row.competicion,
                "partido": row.partido,
                "commence_time": row.commence_time.isoformat() if row.commence_time else None,
                "bookies": [],
                "_partido_normalizado": partido_normalizado,
            }
            bucket.append(grupo_encontrado)

        grupo_encontrado["bookies"].append(entrada_bookie)

    groups = []
    for bucket in grupos_por_liga.values():
        for grupo in bucket:
            grupo.pop("_partido_normalizado", None)
            groups.append(grupo)

    return {
        "total": len(groups),
        "groups": groups,
    }