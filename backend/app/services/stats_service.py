from typing import Optional, List, Dict, Any

from app.models.bet import Bet


def _norm(x: str) -> str:
    return x.strip().lower()


def filter_bets(
    bets: List[Bet],
    estado: Optional[str] = None,
    deporte: Optional[str] = None,
    bookie: Optional[str] = None,
) -> List[Bet]:
    if estado:
        bets = [b for b in bets if _norm(b.estado) == _norm(estado)]
    if deporte:
        bets = [b for b in bets if _norm(b.deporte) == _norm(deporte)]
    if bookie:
        bets = [b for b in bets if _norm(b.bookie) == _norm(bookie)]
    return bets


def compute_stats(bets: List[Bet]) -> Dict[str, Any]:
    settled = [b for b in bets if (b.estado or "").strip().upper() == "SETTLED"]

    total_bets = len(bets)
    settled_bets = len(settled)
    wins = len([b for b in settled if (b.pnl or 0) > 0])
    losses = len([b for b in settled if (b.pnl or 0) < 0])

    total_stake = sum(b.stake for b in settled)
    total_pnl = sum((b.pnl or 0) for b in settled)
    roi = (total_pnl / total_stake * 100) if total_stake > 0 else 0.0

    return {
        "total_bets": total_bets,
        "settled_bets": settled_bets,
        "wins": wins,
        "losses": losses,
        "total_stake": round(total_stake, 2),
        "total_pnl": round(total_pnl, 2),
        "roi_percent": round(roi, 2),
    }
