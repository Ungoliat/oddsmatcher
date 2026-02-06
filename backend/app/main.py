# --- Standard library ---
from pathlib import Path
from typing import Optional
from datetime import datetime
import csv
import shutil

# --- FastAPI ---
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# --- App services ---
from app.services.event_source import load_events_from_csv
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_token,
    ensure_default_users,
)
from app.services.user_repo import list_users
from app.db.database import init_db

# --- App models ---
from app.models.user import UserPublic

from fastapi.middleware.cors import CORSMiddleware

# ======================================================
# APP
# ======================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# CSV PATHS
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/

CSV_BASE_PATH = BASE_DIR / "data" / "apuestas.csv"   # CSV BASE (events)
CSV_BETS_PATH = BASE_DIR / "data" / "bets.csv"       # CSV BETS (futuro)


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
            raise HTTPException(status_code=403, detail="No tienes permisos para este recurso")
        return user

    return checker


# ======================================================
# STARTUP
# ======================================================

@app.on_event("startup")
def on_startup():
    init_db()
    ensure_default_users()


@app.get("/")
def root():
    return {"status": "ok", "msg": "Oddsmatcher API base OK ✅"}


# ======================================================
# EVENTS (CSV BASE)
# ======================================================

@app.get("/events")
def get_events(
    deporte: Optional[str] = None,
    bookie: Optional[str] = None,
    competicion: Optional[str] = None,
    partido: Optional[str] = None,
    limit: int = 200,
    _: UserPublic = Depends(require_role("pro", "admin")),
):
    events = load_events_from_csv(CSV_BASE_PATH)

    if deporte:
        events = [e for e in events if e.get("deporte") == deporte]
    if bookie:
        events = [e for e in events if e.get("bookie") == bookie]
    if competicion:
        q = competicion.strip().lower()
        events = [e for e in events if q in (e.get("competicion", "").lower())]
    if partido:
        q = partido.strip().lower()
        events = [e for e in events if q in (e.get("partido", "").lower())]

    events = events[: max(1, min(limit, 2000))]
    return {"count": len(events), "events": events}


@app.get("/events/filters")
def get_event_filters(
    _: UserPublic = Depends(require_role("pro", "admin")),
):
    events = load_events_from_csv(CSV_BASE_PATH)

    bookies = sorted({e.get("bookie") for e in events if e.get("bookie")})
    deportes = sorted({e.get("deporte") for e in events if e.get("deporte")})
    competiciones = sorted({e.get("competicion") for e in events if e.get("competicion")})
    mercados = sorted({m for e in events for m in (e.get("mercados") or []) if m})

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
):
    if not file.filename.lower().endswith(".csv"):
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

    target_path = CSV_BASE_PATH
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target_path.with_name(f"apuestas_backup_{timestamp}.csv")

    if target_path.exists():
        shutil.copyfile(target_path, backup_path)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(content)

    return {
        "status": "ok",
        "rows_validated": rows_checked,
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


# ======================================================
# AUTH ENDPOINTS
# ======================================================

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")

    token = create_access_token(subject=user.username, role=user.role)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
def me(current_user: UserPublic = Depends(get_current_user)):
    return current_user
