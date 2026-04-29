from typing import Optional, Set

BOOKIES_ES_ALLOWED_EXACT: Set[str] = {
    "888sport",
    "betfair",
    "betsson",
    "betway",
    "bwin",
    "codere",
    "leovegas",
    "luckia",
    "sportium",
    "unibet",
    "bet365",
}

BOOKIES_REFERENCE: Set[str] = {
    "pinnacle",
    "matchbook",
    "sbobet",
    "orbitx",
}


def normalize_bookie_name(bookie: str) -> str:
    return (bookie or "").strip().lower()


def canonicalize_bookie_name(bookie: str) -> Optional[str]:
    bookie_lower = normalize_bookie_name(bookie)

    # Bloquea variantes regionales que no queremos
    blocked_suffixes = ["(it)", "(se)", "(fr)", "(nl)", "(uk)", "(us)", "(au)", "(eu)"]
    if any(suffix in bookie_lower for suffix in blocked_suffixes):
        return None

    if "888" in bookie_lower:
        return "888sport"
    if "bet365" in bookie_lower:
        return "bet365"
    if "betfair" in bookie_lower:
        return "betfair"
    if "betsson" in bookie_lower:
        return "betsson"
    if "betway" in bookie_lower:
        return "betway"
    if "bwin" in bookie_lower:
        return "bwin"
    if "codere" in bookie_lower:
        return "codere"
    if "leovegas" in bookie_lower:
        return "leovegas"
    if "luckia" in bookie_lower:
        return "luckia"
    if "sportium" in bookie_lower:
        return "sportium"
    if "unibet" in bookie_lower:
        return "unibet"

    return None


def is_allowed_es_bookie(bookie: str) -> bool:
    canonical = canonicalize_bookie_name(bookie)
    return canonical in BOOKIES_ES_ALLOWED_EXACT


def is_reference_bookie(bookie: str) -> bool:
    bookie_lower = normalize_bookie_name(bookie)
    return any(reference in bookie_lower for reference in BOOKIES_REFERENCE)