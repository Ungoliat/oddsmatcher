import json
from sqlalchemy.orm import Session
from app.models.event import Event

def replace_events(db: Session, events: list[dict]):
    # Borramos todo lo anterior
    db.query(Event).delete()

    # Insertamos los nuevos
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