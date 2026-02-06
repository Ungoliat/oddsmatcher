from pydantic import BaseModel
from typing import Optional


class Bet(BaseModel):
    id: int
    fecha: str
    deporte: str
    bookie: str
    evento: str
    mercado: str
    cuota: float
    prob: float
    value: float
    kelly_f: float
    bankroll: float
    stake: float
    estado: str
    resultado: Optional[str] = None
    pnl: Optional[float] = None
