import csv
import os
from datetime import datetime

CSV_FILE = "apuestas.csv"

HEADERS = [
    "id",
    "fecha",
    "deporte",
    "bookie",
    "evento",
    "mercado",
    "cuota",
    "prob",
    "value",
    "kelly_f",
    "bankroll",
    "stake",
    "estado",   # OPEN / SETTLED
    "resultado",# WIN / LOSE / VOID / (vacío si OPEN)
    "pnl"       # beneficio/pérdida en €
]


def asegurar_csv(path: str = CSV_FILE) -> None:
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)


def _siguiente_id(path: str = CSV_FILE) -> int:
    asegurar_csv(path)
    with open(path, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        if not rows:
            return 1
        return max(int(r["id"]) for r in rows) + 1


def registrar_apuesta(apuesta: dict, bankroll: float, stake: float, path: str = CSV_FILE) -> int:
    """
    apuesta dict esperado: evento, mercado, cuota, prob, value, kelly_f
    """
    asegurar_csv(path)
    bet_id = _siguiente_id(path)

    row = {
        "id": bet_id,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deporte": apuesta.get("deporte", ""),
        "bookie": apuesta.get("bookie", ""),
        "evento": apuesta["evento"],
        "mercado": apuesta["mercado"],
        "cuota": apuesta["cuota"],
        "prob": apuesta["prob"],
        "value": apuesta["value"],
        "kelly_f": apuesta["kelly_f"],
        "bankroll": bankroll,
        "stake": stake,
        "estado": "OPEN",
        "resultado": "",
        "pnl": "",
    }

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow(row)

    return bet_id


def listar_apuestas(path: str = CSV_FILE) -> list[dict]:
    asegurar_csv(path)
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def liquidar_apuesta(bet_id: int, resultado: str, path: str = CSV_FILE) -> bool:
    """
    resultado: WIN / LOSE / VOID
    PNL:
      - WIN  => stake * (cuota - 1)
      - LOSE => -stake
      - VOID => 0
    """
    asegurar_csv(path)
    rows = listar_apuestas(path)
    updated = False

    for r in rows:
        if int(r["id"]) == bet_id:
            if r["estado"] == "SETTLED":
                return False  # ya liquidada

            stake = float(r["stake"])
            cuota = float(r["cuota"])

            res = resultado.upper().strip()
            if res == "WIN":
                pnl = stake * (cuota - 1)
            elif res == "LOSE":
                pnl = -stake
            elif res == "VOID":
                pnl = 0.0
            else:
                return False

            r["estado"] = "SETTLED"
            r["resultado"] = res
            r["pnl"] = f"{pnl:.2f}"
            updated = True
            break

    if not updated:
        return False

    # Reescribir CSV completo
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    return True

def _to_float(x, default=0.0):
    try:
        if x is None:
            return default
        s = str(x).strip().replace(",", ".")
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def dashboard_resumen(path: str = CSV_FILE) -> dict:
    rows = listar_apuestas(path)

    total = {
        "n_total": len(rows),
        "n_open": 0,
        "n_settled": 0,
        "stake_total_settled": 0.0,
        "pnl_total": 0.0,
        "wins": 0,
        "loses": 0,
        "voids": 0,
    }

    by_bookie = {}
    by_deporte = {}

    def ensure_bucket(d, key):
        if key not in d:
            d[key] = {
                "n_open": 0,
                "n_settled": 0,
                "stake_total_settled": 0.0,
                "pnl_total": 0.0,
                "wins": 0,
                "loses": 0,
                "voids": 0,
            }

    for r in rows:
        estado = (r.get("estado") or "").strip().upper()
        resultado = (r.get("resultado") or "").strip().upper()

        stake = _to_float(r.get("stake"), 0.0)
        pnl = _to_float(r.get("pnl"), 0.0)

        bookie = (r.get("bookie") or "").strip() or "SIN_BOOKIE"
        deporte = (r.get("deporte") or "").strip() or "SIN_DEPORTE"

        ensure_bucket(by_bookie, bookie)
        ensure_bucket(by_deporte, deporte)

        if estado == "OPEN":
            total["n_open"] += 1
            by_bookie[bookie]["n_open"] += 1
            by_deporte[deporte]["n_open"] += 1

        elif estado == "SETTLED":
            total["n_settled"] += 1
            total["stake_total_settled"] += stake
            total["pnl_total"] += pnl

            by_bookie[bookie]["n_settled"] += 1
            by_bookie[bookie]["stake_total_settled"] += stake
            by_bookie[bookie]["pnl_total"] += pnl

            by_deporte[deporte]["n_settled"] += 1
            by_deporte[deporte]["stake_total_settled"] += stake
            by_deporte[deporte]["pnl_total"] += pnl

            if resultado == "WIN":
                total["wins"] += 1
                by_bookie[bookie]["wins"] += 1
                by_deporte[deporte]["wins"] += 1
            elif resultado == "LOSE":
                total["loses"] += 1
                by_bookie[bookie]["loses"] += 1
                by_deporte[deporte]["loses"] += 1
            elif resultado == "VOID":
                total["voids"] += 1
                by_bookie[bookie]["voids"] += 1
                by_deporte[deporte]["voids"] += 1

    stake_settled = total["stake_total_settled"]
    total["roi"] = (total["pnl_total"] / stake_settled) if stake_settled > 0 else 0.0
    denom = (total["wins"] + total["loses"])
    total["winrate"] = (total["wins"] / denom) if denom > 0 else 0.0

    def finalize_bucket(b):
        stake = b["stake_total_settled"]
        b["roi"] = (b["pnl_total"] / stake) if stake > 0 else 0.0
        denom = (b["wins"] + b["loses"])
        b["winrate"] = (b["wins"] / denom) if denom > 0 else 0.0
        return b

    by_bookie = {k: finalize_bucket(v) for k, v in by_bookie.items()}
    by_deporte = {k: finalize_bucket(v) for k, v in by_deporte.items()}

    return {"total": total, "by_bookie": by_bookie, "by_deporte": by_deporte}
