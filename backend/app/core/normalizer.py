from thefuzz import fuzz

# Diccionario de traducción español → inglés para equipos comunes
TRADUCCION_EQUIPOS = {
    # Francia
    "marsella": "marseille",
    "lyon": "lyon",
    "paris saint-germain": "paris saint-germain",
    "psg": "paris saint-germain",
    "niza": "nice",
    "nantes": "nantes",
    "lens": "lens",
    "lille": "lille",
    "monaco": "monaco",
    "rennes": "rennes",
    "estrasburgo": "strasbourg",
    "toulouse": "toulouse",
    "brest": "brest",
    "reims": "reims",
    "montpellier": "montpellier",
    "le havre": "le havre",
    "angers": "angers",
    "auxerre": "auxerre",
    "saint-etienne": "saint-etienne",
    # España
    "atletico de madrid": "atletico madrid",
    "atletico madrid": "atletico madrid",
    "athletic bilbao": "athletic bilbao",
    "athletic club": "athletic bilbao",
    "real sociedad": "real sociedad",
    "real betis": "real betis",
    "betis": "real betis",
    "villarreal": "villarreal",
    "mallorca": "mallorca",
    "girona": "girona",
    "celta vigo": "celta vigo",
    "celta de vigo": "celta vigo",
    "alaves": "alaves",
    "deportivo alaves": "alaves",
    "getafe": "getafe",
    "rayo vallecano": "rayo vallecano",
    "osasuna": "osasuna",
    "las palmas": "las palmas",
    "valencia": "valencia",
    "espanyol": "espanyol",
    "leganes": "leganes",
    "valladolid": "valladolid",
    "real valladolid": "valladolid",
    # Alemania
    "borussia monchengladbach": "borussia monchengladbach",
    "borussia mönchengladbach": "borussia monchengladbach",
    "colonia": "fc cologne",
    "fc colonia": "fc cologne",
    "bayer leverkusen": "bayer leverkusen",
    "borussia dortmund": "borussia dortmund",
    "bayern munich": "bayern munich",
    "bayern münchen": "bayern munich",
    "eintracht frankfurt": "eintracht frankfurt",
    "rb leipzig": "rb leipzig",
    "union berlin": "union berlin",
    "1. fc union berlin": "union berlin",
    "wolfsburgo": "wolfsburg",
    "friburgo": "freiburg",
    "sc friburgo": "freiburg",
    "augsburgo": "augsburg",
    "mainz": "mainz",
    "hoffenheim": "hoffenheim",
    "werder bremen": "werder bremen",
    "stuttgart": "stuttgart",
    "heidenheim": "heidenheim",
    "holstein kiel": "holstein kiel",
    "st. pauli": "st pauli",
    # Italia
    "milan": "ac milan",
    "ac milan": "ac milan",
    "inter": "inter milan",
    "inter milan": "inter milan",
    "internazionale": "inter milan",
    "juventus": "juventus",
    "napoles": "napoli",
    "napoli": "napoli",
    "roma": "roma",
    "lazio": "lazio",
    "atalanta": "atalanta",
    "fiorentina": "fiorentina",
    "torino": "torino",
    "bolonia": "bologna",
    "bologna": "bologna",
    "udinese": "udinese",
    "sassuolo": "sassuolo",
    "monza": "monza",
    "genoa": "genoa",
    "lecce": "lecce",
    "cagliari": "cagliari",
    "verona": "verona",
    "hellas verona": "verona",
    "empoli": "empoli",
    "venezia": "venezia",
    "como": "como",
    "parma": "parma",
    # Inglaterra
    "manchester city": "manchester city",
    "manchester united": "manchester united",
    "arsenal": "arsenal",
    "chelsea": "chelsea",
    "liverpool": "liverpool",
    "tottenham": "tottenham",
    "tottenham hotspur": "tottenham",
    "newcastle": "newcastle",
    "newcastle united": "newcastle",
    "aston villa": "aston villa",
    "west ham": "west ham",
    "west ham united": "west ham",
    "brighton": "brighton",
    "fulham": "fulham",
    "brentford": "brentford",
    "crystal palace": "crystal palace",
    "wolverhampton": "wolverhampton",
    "wolves": "wolverhampton",
    "everton": "everton",
    "nottingham forest": "nottingham forest",
    "leicester": "leicester",
    "leicester city": "leicester",
    "ipswich": "ipswich",
    "ipswich town": "ipswich",
    "southampton": "southampton",
    "bournemouth": "bournemouth",
}


def normalizar_nombre_equipo(nombre: str) -> str:
    """Normaliza el nombre de un equipo eliminando sufijos comunes."""
    nombre = nombre.strip()

    # Eliminar sufijos comunes
    sufijos = [
        " FC", " CF", " SC", " AC", " BC", " SD", " UD", " CD",
        " Athletic", " Atletico", " Deportivo",
    ]

    nombre_norm = nombre
    for sufijo in sufijos:
        nombre_norm = nombre_norm.replace(sufijo, "")

    # Normalizar separador de partido
    nombre_norm = nombre_norm.replace(" v ", " vs ")

    # Normalizar caracteres especiales
    nombre_norm = nombre_norm.replace("ö", "o").replace("ü", "u").replace("ä", "a")
    nombre_norm = nombre_norm.replace("é", "e").replace("è", "e").replace("ê", "e")
    nombre_norm = nombre_norm.replace("á", "a").replace("à", "a")
    nombre_norm = nombre_norm.replace("í", "i").replace("ó", "o").replace("ú", "u")
    nombre_norm = nombre_norm.replace("ñ", "n")

    nombre_norm = nombre_norm.strip().lower()

    # Aplicar traducción si existe
    if nombre_norm in TRADUCCION_EQUIPOS:
        nombre_norm = TRADUCCION_EQUIPOS[nombre_norm]

    return nombre_norm


def normalizar_partido(partido: str) -> str:
    """Normaliza un partido completo 'Equipo1 vs Equipo2'."""
    if " vs " in partido:
        partes = partido.split(" vs ")
    elif " v " in partido:
        partes = partido.split(" v ")
    else:
        return normalizar_nombre_equipo(partido)

    home = normalizar_nombre_equipo(partes[0])
    away = normalizar_nombre_equipo(partes[1])
    return f"{home} vs {away}"


def emparejar_partido(partido_betfair: str, partidos_oddspapi: list, umbral: int = 75) -> str | None:
    """
    Empareja un partido de Betfair con uno de OddsPapi usando fuzzy matching.
    """
    mejor_ratio = 0
    mejor_match = None

    betfair_norm = normalizar_partido(partido_betfair)

    for partido in partidos_oddspapi:
        oddspapi_norm = normalizar_partido(partido)
        ratio = max(
            fuzz.token_sort_ratio(betfair_norm, oddspapi_norm),
            fuzz.partial_ratio(betfair_norm, oddspapi_norm)
        )
        if ratio > mejor_ratio:
            mejor_ratio = ratio
            mejor_match = partido

    if mejor_ratio >= umbral:
        return mejor_match
    return None


def emparejar_equipo(nombre_betfair: str, nombres_oddspapi: list, umbral: int = 70) -> str | None:
    """Empareja un nombre de equipo de Betfair con uno de OddsPapi."""
    mejor_ratio = 0
    mejor_match = None

    betfair_norm = normalizar_nombre_equipo(nombre_betfair)

    for nombre in nombres_oddspapi:
        oddspapi_norm = normalizar_nombre_equipo(nombre)
        ratio = fuzz.token_sort_ratio(betfair_norm, oddspapi_norm)
        if ratio > mejor_ratio:
            mejor_ratio = ratio
            mejor_match = nombre

    if mejor_ratio >= umbral:
        return mejor_match
    return None