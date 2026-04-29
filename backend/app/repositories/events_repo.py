import json
from sqlalchemy.orm import Session
from app.models.event import Event


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

    grouped = {}

    for row in rows:
        group_key = f"{row.deporte}||{row.competicion}||{row.partido}"

        if group_key not in grouped:
            grouped[group_key] = {
                "deporte": row.deporte,
                "competicion": row.competicion,
                "partido": row.partido,
                "commence_time": row.commence_time.isoformat() if row.commence_time else None,
                "bookies": [],
            }

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

        grouped[group_key]["bookies"].append({
            "bookie": row.bookie,
            "mercados": sorted(set(mercados)),
            "cuotas": cuotas,
        })

    groups = list(grouped.values())

    return {
        "total": len(groups),
        "groups": groups,
    }