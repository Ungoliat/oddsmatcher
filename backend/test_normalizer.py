import sys
sys.path.insert(0, ".")
from app.core.normalizer import emparejar_partido

# Partidos de Betfair
partidos_betfair = [
    "Leeds v Burnley",
    "Girona v Mallorca",
    "Pisa v Lecce",
]

# Partidos de OddsPapi
partidos_oddspapi = [
    "Leeds United vs Burnley FC",
    "Girona vs Mallorca",
    "Pisa vs Lecce",
    "Barcelona vs Real Madrid",
    "Arsenal vs Fulham",
]

for partido_bf in partidos_betfair:
    match = emparejar_partido(partido_bf, partidos_oddspapi)
    print(f"Betfair: '{partido_bf}' → OddsPapi: '{match}'")