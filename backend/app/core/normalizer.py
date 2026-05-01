from thefuzz import fuzz


def normalizar_nombre_equipo(nombre: str) -> str:
    """Normaliza el nombre de un equipo eliminando sufijos comunes."""
    nombre = nombre.strip()
    
    # Eliminar sufijos comunes
    sufijos = [
        " FC", " CF", " SC", " AC", " BC", " SD", " UD", " CD",
        " United", " City", " Town", " Wanderers", " Hotspur",
        " Athletic", " Atletico", " Deportivo",
        " v ", " vs ",
    ]
    
    nombre_norm = nombre
    for sufijo in sufijos:
        nombre_norm = nombre_norm.replace(sufijo, "")
    
    return nombre_norm.strip().lower()


def emparejar_partido(partido_betfair: str, partidos_oddspapi: list, umbral: int = 75) -> str | None:
    """
    Empareja un partido de Betfair con uno de OddsPapi usando fuzzy matching.
    
    partido_betfair: "Leeds v Burnley"
    partidos_oddspapi: lista de strings "Leeds United vs Burnley FC"
    
    Retorna el partido de OddsPapi más parecido o None si no supera el umbral.
    """
    mejor_ratio = 0
    mejor_match = None

    betfair_norm = normalizar_nombre_equipo(partido_betfair)

    for partido in partidos_oddspapi:
        oddspapi_norm = normalizar_nombre_equipo(partido)
        ratio = fuzz.token_sort_ratio(betfair_norm, oddspapi_norm)
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