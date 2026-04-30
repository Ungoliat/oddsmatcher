# --- Standard library ---
from pathlib import Path
from typing import Optional
from datetime import datetime
import csv
import shutil
import json

# --- FastAPI ---
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

# --- DB ---
from sqlalchemy.orm import Session
from app.db.session import engine, get_db
from app.db.base import Base
import app.models

# --- App services ---
from app.services.event_source import load_events_from_csv
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_token,
    ensure_default_users,
)
from app.services.user_repo import list_users

# --- Repositories ---
from app.repositories.events_repo import (
    get_events as get_events_db,
    replace_events,
    get_grouped_events,
)

# --- Models ---
from app.models.user import UserPublic
from app.models.event import Event

# --- Sync providers ---
from app.services.providers.mock_provider import MockOddsProvider
from app.services.providers.the_odds_api_provider import TheOddsApiProvider
from app.services.sync_service import sync_events_from_provider

from app.db.base import Base
from app.db.session import engine
from app.db.migrations import run_sqlite_safe_migrations
# --- Cache ---
EVENTS_CACHE = []

# ======================================================
# APP
# ======================================================

app = FastAPI()

Base.metadata.create_all(bind=engine)
run_sqlite_safe_migrations(engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# CSV PATHS
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
CSV_BASE_PATH = BASE_DIR / "data" / "apuestas.csv"
CSV_BETS_PATH = BASE_DIR / "data" / "bets.csv"

# ======================================================
# CSV BASE CONTRACT (D4)
# ======================================================

REQUIRED_COLUMNS = {
    "bookie",
    "competicion",
    "partido",
    "mercados",
    "deporte",
}

# ======================================================
# AUTH
# ======================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    payload = decode_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserPublic(
        username=payload["sub"],
        role=payload.get("role", "free"),
        disabled=False,
    )


def require_role(*allowed_roles: str):
    def checker(user: UserPublic = Depends(get_current_user)) -> UserPublic:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para este recurso",
            )
        return user

    return checker


# ======================================================
# STARTUP
# ======================================================

@app.on_event("startup")
def on_startup():
    ensure_default_users()


@app.get("/")
def root():
    return {"status": "ok", "msg": "Oddsmatcher API base OK ✅"}


# ======================================================
# EVENTS
# ======================================================

@app.get("/events")
def get_events(
    deporte: Optional[str] = None,
    bookie: Optional[str] = None,
    mercado: Optional[str] = None,
    competicion: Optional[str] = None,
    partido: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    _: UserPublic = Depends(require_role("pro", "admin")),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 2000))
    offset = max(0, offset)

    return get_events_db(
        db=db,
        limit=limit,
        offset=offset,
        deporte=deporte,
        bookie=bookie,
        mercado=mercado,
        competicion=competicion,
        partido=partido,
    )

@app.get("/events/grouped")
def read_grouped_events(
    deporte: str | None = None,
    competicion: str | None = None,
    partido: str | None = None,
    bookie: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("pro", "admin")),
):
    return get_grouped_events(
        db=db,
        deporte=deporte,
        competicion=competicion,
        partido=partido,
        bookie=bookie,
    )

@app.get("/events/filters")
def get_event_filters(
    _: UserPublic = Depends(require_role("pro", "admin")),
    db: Session = Depends(get_db),
):
    bookies = sorted({row[0] for row in db.query(Event.bookie).distinct().all() if row[0]})
    deportes = sorted({row[0] for row in db.query(Event.deporte).distinct().all() if row[0]})
    competiciones = sorted({row[0] for row in db.query(Event.competicion).distinct().all() if row[0]})

    rows = db.query(Event.mercados).all()
    mercados_set = set()

    for row in rows:
        raw = row[0]
        if not raw:
            continue

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for m in parsed:
                    if m:
                        mercados_set.add(str(m).strip())
            else:
                mercados_set.add(str(parsed).strip())
        except Exception:
            for m in str(raw).split(","):
                m = m.strip()
                if m:
                    mercados_set.add(m)

    mercados = sorted(mercados_set)

    return {
        "bookies": bookies,
        "deportes": deportes,
        "competiciones": competiciones,
        "mercados": mercados,
    }


# ======================================================
# ADMIN
# ======================================================

@app.get("/admin/users")
def admin_list_users(_: UserPublic = Depends(require_role("admin"))):
    return {"users": list_users()}


@app.post("/admin/upload-csv")
async def admin_upload_csv(
    file: UploadFile = File(...),
    _: UserPublic = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    global EVENTS_CACHE

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .csv")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El CSV está vacío")

    try:
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(decoded.splitlines())
    except Exception:
        raise HTTPException(status_code=400, detail="CSV inválido")

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="El CSV no tiene cabecera")

    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Faltan columnas obligatorias: {', '.join(sorted(missing))}",
        )

    rows_checked = 0
    for i, row in enumerate(reader, start=1):
        rows_checked += 1
        for col in REQUIRED_COLUMNS:
            if not (row.get(col) or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"Fila {i}: el campo '{col}' está vacío",
                )

    if rows_checked == 0:
        raise HTTPException(status_code=400, detail="El CSV no contiene datos")

    reader_for_db = csv.DictReader(decoded.splitlines())
    events = []

    for row in reader_for_db:
        mercados = [m.strip() for m in row["mercados"].split(",") if m.strip()]

        events.append(
            {
                "bookie": row["bookie"].strip(),
                "competicion": row["competicion"].strip(),
                "partido": row["partido"].strip(),
                "deporte": row["deporte"].strip(),
                "mercados": mercados,
            }
        )

    target_path = CSV_BASE_PATH
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target_path.with_name(f"apuestas_backup_{timestamp}.csv")

    if target_path.exists():
        shutil.copyfile(target_path, backup_path)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(content)

    EVENTS_CACHE = load_events_from_csv(CSV_BASE_PATH)
    print(f"🔥 Cache recargado tras upload: {len(EVENTS_CACHE)}")

    replace_events(db, events)
    print(f"💾 Eventos guardados en DB: {len(events)}")

    return {
        "status": "ok",
        "rows_validated": rows_checked,
        "rows_inserted": len(events),
        "uploaded_as": str(target_path),
        "backup_created": str(backup_path) if backup_path.exists() else None,
    }


@app.get("/admin/csv-info")
def admin_csv_info(_: UserPublic = Depends(require_role("admin"))):
    if not CSV_BASE_PATH.exists():
        raise HTTPException(status_code=404, detail="No hay CSV cargado")

    stat = CSV_BASE_PATH.stat()

    with open(CSV_BASE_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return {
        "path": str(CSV_BASE_PATH),
        "rows": len(rows),
        "columns": reader.fieldnames,
        "sample_row": rows[0] if rows else None,
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


@app.post("/admin/sync-api")
def sync_api(
    _: UserPublic = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    provider = MockOddsProvider()
    result = sync_events_from_provider(db=db, provider=provider)
    return result


@app.post("/admin/sync-api-real")
def sync_api_real(
    _: UserPublic = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    provider = TheOddsApiProvider()
    result = sync_events_from_provider(db=db, provider=provider)
    return result

@app.post("/admin/sync-oddspapi")
def sync_oddspapi(
    _: UserPublic = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from app.services.providers.oddspapi_provider import OddsPapiProvider
    from app.services.sync_service_oddspapi import sync_events_from_oddspapi
    result = sync_events_from_oddspapi(db=db, provider=OddsPapiProvider())
    return result

@app.get("/odds/matching")
def get_matching_odds(
    comision: float = 0.02,
    db: Session = Depends(get_db),
    _: UserPublic = Depends(require_role("pro", "admin")),
):
    from app.repositories.events_repo import get_grouped_events
    import json

    data = get_grouped_events(db=db)
    groups = data.get("groups", [])

    oportunidades = []

    for group in groups:
        partido = group["partido"]
        competicion = group["competicion"]
        deporte = group["deporte"]

        # Separar bookies normales y betfair
        betfair = next((b for b in group["bookies"] if b["bookie"] == "betfair"), None)
        casas = [b for b in group["bookies"] if b["bookie"] != "betfair"]

        if not betfair:
            continue

        for casa in casas:
            bookie = casa["bookie"]

            for mercado, outcomes_back in casa["cuotas"].items():
                if mercado not in betfair["cuotas"]:
                    continue

                outcomes_lay = betfair["cuotas"][mercado]

                for outcome, back_odds in outcomes_back.items():
                    if outcome not in outcomes_lay:
                        continue

                    lay_odds = outcomes_lay[outcome]

                    if lay_odds <= 1:
                        continue

                    # Calculo con back_stake = 100 como referencia
                    back_stake = 100
                    lay_stake = (back_stake * back_odds) / (lay_odds - comision)
                    ganancia_back = back_stake * (back_odds - 1)
                    perdida_lay = lay_stake * (lay_odds - 1)
                    resultado_neto = ganancia_back - perdida_lay
                    rating = (back_stake + resultado_neto) / back_stake * 100

                    oportunidades.append({
                        "competicion": competicion,
                        "partido": partido,
                        "outcome": outcome,
                        "mercado": mercado,
                        "bookie": bookie,
                        "back_odds": back_odds,
                        "lay_odds": lay_odds,
                        "lay_stake": round(lay_stake, 2),
                        "resultado_neto": round(resultado_neto, 2),
                        "rating": round(rating, 2),
                        "commence_time": group.get("commence_time"),
                    })
    oportunidades = [o for o in oportunidades if 85 <= o["rating"] <= 102]
    oportunidades.sort(key=lambda x: x["rating"], reverse=True)

    return {
        "comision": comision,
        "total": len(oportunidades),
        "oportunidades": oportunidades,
    }

    # ======================================================
# LEDGER (apuestas del usuario)
# ======================================================

@app.get("/bets")
def get_bets(current_user: UserPublic = Depends(get_current_user)):
    from app.repositories.bets_repo import list_bets
    return {"bets": list_bets(current_user.username)}


@app.post("/bets")
def add_bet(
    data: dict,
    current_user: UserPublic = Depends(get_current_user),
):
    from app.repositories.bets_repo import create_bet
    bet = create_bet(username=current_user.username, data=data)
    return bet


@app.patch("/bets/{bet_id}")
def update_bet(
    bet_id: int,
    data: dict,
    current_user: UserPublic = Depends(get_current_user),
):
    from app.repositories.bets_repo import update_bet as update_bet_repo
    bet = update_bet_repo(bet_id=bet_id, username=current_user.username, data=data)
    if not bet:
        raise HTTPException(status_code=404, detail="Apuesta no encontrada")
    return bet


@app.delete("/bets/{bet_id}")
def delete_bet(
    bet_id: int,
    current_user: UserPublic = Depends(get_current_user),
):
    from app.repositories.bets_repo import delete_bet as delete_bet_repo
    delete_bet_repo(bet_id=bet_id, username=current_user.username)
    return {"ok": True}
# ======================================================
# AUTH ENDPOINTS
# ======================================================

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Usuario o contraseña incorrectos",
        )

    token = create_access_token(subject=user.username, role=user.role)

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@app.get("/me")
def me(current_user: UserPublic = Depends(get_current_user)):
    return current_user

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"version": "v1.0"}