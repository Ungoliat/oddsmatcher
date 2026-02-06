from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def ensure_csv_with_header(csv_path: Path, header: list[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)


def append_row(csv_path: Path, row: Dict[str, Any], header: list[str]) -> None:
    ensure_csv_with_header(csv_path, header)
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writerow(row)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def ask_float(prompt: str, min_value: float | None = None, max_value: float | None = None) -> float:
    """
    Pide un número por teclado. Acepta coma o punto decimal.
    """
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            print("❌ Introduce un número válido (ej: 2.50).")
            continue

        if min_value is not None and value < min_value:
            print(f"❌ Debe ser >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"❌ Debe ser <= {max_value}.")
            continue
        return value


def ask_yes_no(prompt: str) -> bool:
    while True:
        raw = input(prompt).strip().lower()
        if raw in ("s", "si", "sí", "y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("❌ Responde s/n.")

def ask_lines(prompt: str) -> list[str]:
    """
    Lee múltiples líneas hasta que el usuario pulse Enter en una línea vacía.
    """
    print(prompt)
    lines: list[str] = []
    while True:
        line = input().strip()
        if line == "":
            break
        lines.append(line)
    return lines
