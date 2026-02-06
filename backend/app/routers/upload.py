from fastapi import APIRouter, UploadFile, File, HTTPException
import csv
import io

router = APIRouter(
    prefix="/upload",
    tags=["Upload CSV"]
)
@router.post("/csv")
async def upload_csv(file: UploadFile = File(...)):

    # 1️⃣ Validar extensión
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un CSV (.csv)"
        )

    content = await file.read()

    # 2️⃣ Validar que no esté vacío
    if not content:
        raise HTTPException(
            status_code=400,
            detail="El CSV está vacío"
        )

    # 3️⃣ Leer CSV
    try:
        decoded = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="No se pudo leer el CSV (codificación inválida)"
        )

    # 4️⃣ Validar cabecera
    if not reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="El CSV no tiene cabecera"
        )

    required_columns = {
        "bookie",
        "competicion",
        "partido",
        "mercados",
        "deporte"
    }

    missing = required_columns - set(reader.fieldnames)

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Faltan columnas obligatorias: {', '.join(missing)}"
        )

    # 5️⃣ Validar filas
    rows = list(reader)

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="El CSV no contiene datos"
        )

    for index, row in enumerate(rows, start=1):
        for field in required_columns:
            if not row.get(field) or not row[field].strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"Fila {index}: el campo '{field}' está vacío"
                )

    # ✅ Todo correcto
    return {
        "status": "ok",
        "rows_validated": len(rows),
        "message": "CSV validado correctamente"
    }
