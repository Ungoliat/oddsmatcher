def lay_stake(back_stake: float, back_odds: float, lay_odds: float, commission: float = 0.0) -> float:
    return (back_stake * back_odds) / (lay_odds - commission)


def lay_liability(lay_stake_value: float, lay_odds: float) -> float:
    return lay_stake_value * (lay_odds - 1)


def outcomes(back_stake: float, back_odds: float, lay_odds: float, commission: float = 0.0) -> dict:
    L = lay_stake(back_stake, back_odds, lay_odds, commission)
    liability = lay_liability(L, lay_odds)

    profit_if_win = back_stake * (back_odds - 1) - liability
    profit_if_lose = -back_stake + (L * (1 - commission))

    return {
        "lay_stake": L,
        "lay_liability": liability,
        "profit_if_win": profit_if_win,
        "profit_if_lose": profit_if_lose,
    }


def expected_value_back_lay(
    back_stake: float,
    back_odds: float,
    lay_odds: float,
    probability_win: float,
    commission: float = 0.0
) -> float:
    res = outcomes(back_stake, back_odds, lay_odds, commission)
    return (
        probability_win * res["profit_if_win"]
        + (1 - probability_win) * res["profit_if_lose"]
    )
def yield_percent(profit: float, max_exposure: float) -> float:
    """
    Yield (%) = beneficio / capital máximo comprometido.
    """
    if max_exposure <= 0:
        return 0.0
    return (profit / max_exposure) * 100.0


def oddsmatcher_summary(
    back_stake: float,
    back_odds: float,
    lay_odds: float,
    commission: float = 0.0,
    min_profit: float = 0.10,
    min_yield_pct: float = 0.0,
) -> dict:
    """
    Resumen tipo Oddsmatcher:
    - Calcula LAY stake, liability y beneficios igualados.
    - Calcula capital máximo expuesto (max(back_stake, liability)).
    - Devuelve si pasa filtros de oportunidad.
    """
    res = outcomes(back_stake, back_odds, lay_odds, commission)

    # En igualado, ambos profits deberían ser casi iguales; tomamos el menor por seguridad
    profit = min(res["profit_if_win"], res["profit_if_lose"])

    max_exposure = max(back_stake, res["lay_liability"])
    yield_exposure_pct = yield_percent(profit, max_exposure)

    yield_stake_pct = yield_percent(profit, back_stake)

    yld = yield_exposure_pct  # mantenemos compatibilidad (yield_pct = exposure)


    is_opportunity = (profit >= min_profit) and (yld >= min_yield_pct)

    return {
    **res,
    "profit_equalized": profit,
    "max_exposure": max_exposure,

    # Yields
    "yield_pct": yld,
    "yield_exposure_pct": yield_exposure_pct,
    "yield_stake_pct": yield_stake_pct,

    "is_opportunity": is_opportunity,
    "min_profit": min_profit,
    "min_yield_pct": min_yield_pct,
}

