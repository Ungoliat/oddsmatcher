import re
import unicodedata
from typing import Dict, Any, List


# --- helpers ---
def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _slug(s: str) -> str:
    s = _strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9]+", "", s)  # solo alfanum
    return s


# --- mappers (ampliables) ---
BOOKIE_ALIASES = {
    "bet365": {"bet365", "bet 365", "bet-365"},
    "betfair": {"betfair", "bet fair"},
    "bwin": {"bwin"},
    "codere": {"codere"},
    "retabet": {"retabet", "reta bet"},
    "winamax": {"winamax", "wina max"},
    "versus": {"versus"},
    "williamhill": {"william hill", "williamhill", "william-hill"},
}

SPORT_ALIASES = {
    "football": {"futbol", "fútbol", "football", "soccer"},
    "tennis": {"tenis", "tennis"},
    "basketball": {"baloncesto", "basket", "basketball"},
    "baseball": {"beisbol", "béisbol", "baseball"},
    "esports": {"esports", "e-sports"},
}


def normalize_bookie(value: str) -> str:
    v = _clean_spaces(value or "")
    v_slug = _slug(v)

    # intenta por alias exacto/slug
    for canon, aliases in BOOKIE_ALIASES.items():
        for a in aliases:
            if _slug(a) == v_slug:
                return canon

    # fallback: slug del texto
    return v_slug


def normalize_sport(value: str) -> str:
    v = _clean_spaces(value or "")
    v_slug = _slug(v)

    for canon, aliases in SPORT_ALIASES.items():
        for a in aliases:
            if _slug(a) == v_slug:
                return canon

    return v_slug


def normalize_competition(value: str) -> str:
    return _clean_spaces(value or "")


def normalize_match(value: str) -> str:
    v = _clean_spaces(value or "")
    # normalizar separador vs
    v = re.sub(r"\s+v\.?\s+", " vs ", v, flags=re.IGNORECASE)
    v = re.sub(r"\s+vs\.?\s+", " vs ", v, flags=re.IGNORECASE)
    return _clean_spaces(v)


def normalize_markets(value: str) -> List[str]:
    """
    Normaliza mercados a códigos canónicos.
    Entrada típica:
    - "1X2"
    - "FT 1X2; Over/Under 2.5; Ambos Marcan"
    - "Match Odds | O/U | BTTS"
    - "Doble oportunidad, DNB"
    Devuelve lista de códigos: ["1X2","OU","BTTS"...] sin duplicados.
    """
    raw = _clean_spaces(value or "")
    if not raw:
        return []

    # Separadores típicos SIN partir "Over/Under"
    parts = re.split(r"[;,|]+", raw)

    # alias -> canon
    alias_map = {
        # 1X2
        "1x2": "1X2",
        "ft 1x2": "1X2",
        "fulltime 1x2": "1X2",
        "match odds": "1X2",
        "resultado final": "1X2",
        "ganador del partido": "1X2",

        # Over/Under
        "over/under": "OU",
        "o/u": "OU",
        "ou": "OU",
        "over under": "OU",
        "total goles": "OU",
        "totales": "OU",

        # BTTS
        "btts": "BTTS",
        "ambos marcan": "BTTS",
        "both teams to score": "BTTS",
        "both teams score": "BTTS",

        # Double chance
        "doble oportunidad": "DC",
        "double chance": "DC",
        "dc": "DC",

        # Asian handicap
        "handicap asiatico": "AH",
        "hándicap asiático": "AH",
        "asian handicap": "AH",
        "ah": "AH",

        # Draw no bet
        "draw no bet": "DNB",
        "empate apuesta no valida": "DNB",
        "empate apuesta no válida": "DNB",
        "dnb": "DNB",
    }

    out: List[str] = []
    seen = set()

    for p in parts:
        p2 = _clean_spaces(p)
        if not p2:
            continue

        p2_low = _strip_accents(p2.lower())

        # Limpieza extra: quitar "2.5", "3.0" etc para reconocer OU
        p2_low_no_nums = re.sub(r"\b\d+(\.\d+)?\b", "", p2_low).strip()
        p2_low_no_nums = _clean_spaces(p2_low_no_nums)

        canon = None

        # match directo
        if p2_low in alias_map:
            canon = alias_map[p2_low]
        elif p2_low_no_nums in alias_map:
            canon = alias_map[p2_low_no_nums]
        else:
            # Heurísticas simples
            if "1x2" in p2_low:
                canon = "1X2"
            elif "over/under" in p2_low or "over under" in p2_low or "o/u" in p2_low:
                canon = "OU"
            elif "ambos" in p2_low and "marcan" in p2_low:
                canon = "BTTS"
            elif "double chance" in p2_low or "doble oportunidad" in p2_low:
                canon = "DC"
            elif "asian handicap" in p2_low or "handicap asiatico" in p2_low or "hándicap" in p2_low:
                canon = "AH"
            elif "draw no bet" in p2_low or "empate apuesta no" in p2_low:
                canon = "DNB"

        # si no se reconoce, guardamos la versión limpia original (para no perder info)
        if canon is None:
            canon = _clean_spaces(p2)

        if canon not in seen:
            seen.add(canon)
            out.append(canon)

    return out



def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    row: dict con keys: bookie, competicion, partido, mercados, deporte
    Devuelve el row normalizado.
    """
    out = dict(row)

    out["bookie"] = normalize_bookie(out.get("bookie", ""))
    out["deporte"] = normalize_sport(out.get("deporte", ""))
    out["competicion"] = normalize_competition(out.get("competicion", ""))
    out["partido"] = normalize_match(out.get("partido", ""))
    out["mercados"] = normalize_markets(out.get("mercados", ""))

    return out
