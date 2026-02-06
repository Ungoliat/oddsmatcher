from pathlib import Path
from typing import Any, Dict, List, Tuple

# Importamos funciones del motor
from volatility_engine.kpis import (
    volatility_index_by_league,
    fi_ci_real_from_goals,
    hot_fixtures,
)

# Si algún día quieres cambiar paths, lo haces aquí
DATA_DIR = Path("volatility_engine/data")


def get_volatility_dashboard() -> Dict[str, Any]:
    """
    Resumen para pintar en la web: VI por liga, top equipos (FI/CI real)
    y lista de fixtures calientes.
    """
    vi = volatility_index_by_league()

    plus2_total, FI_real, minus2_total, CI_real = fi_ci_real_from_goals()

    top_fi = sorted(FI_real.items(), key=lambda x: x[1], reverse=True)[:10]
    top_ci = sorted(CI_real.items(), key=lambda x: x[1], reverse=True)[:10]

    # fixtures calientes (si no existe fixtures.csv, lanzará FileNotFoundError)
    try:
        hot = hot_fixtures(top_n=20)
        hot_list = [
            {"heat": h, "date": d, "league": l, "home": ho, "away": aw}
            for (h, d, l, ho, aw) in hot
        ]
    except FileNotFoundError:
        hot_list = []

    return {
        "vi_by_league": vi,
        "top_fragility_real": [
            {"team": t, "fi_real": v, "plus2_cases": plus2_total.get(t, 0)}
            for (t, v) in top_fi
        ],
        "top_comeback_real": [
            {"team": t, "ci_real": v, "minus2_cases": minus2_total.get(t, 0)}
            for (t, v) in top_ci
        ],
        "hot_fixtures": hot_list,
        "notes": {
            "fixtures_file_required": "volatility_engine/data/fixtures.csv"
        },
    }
