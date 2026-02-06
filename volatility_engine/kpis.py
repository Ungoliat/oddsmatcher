# volatility_engine/kpis.py

from pathlib import Path
import csv
import math
from collections import defaultdict


# =========================
# PATHS
# =========================

MATCHES_PATH = Path("volatility_engine/data/matches_volatility.csv")
GOALS_PATH = Path("volatility_engine/data/goal_events.csv")
FIXTURES_PATH = Path("volatility_engine/data/fixtures.csv")


# =========================
# KPI 1 — VOLATILITY INDEX
# =========================

def volatility_index_by_league():
    total = defaultdict(int)
    hits = defaultdict(int)

    with MATCHES_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            league = row["league"]
            total[league] += 1
            if row["had_event"] == "1":
                hits[league] += 1

    return {lg: hits[lg] / total[lg] for lg in total}


# =========================
# KPI 2–3 (BÁSICO) — FI / CI (solo eventos)
# =========================

def fragility_and_comeback_stats():
    plus2_total = defaultdict(int)
    minus2_total = defaultdict(int)

    with MATCHES_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["had_event"] != "1":
                continue

            home = row["home"]
            away = row["away"]
            side = row["side_with_plus2"]

            if side == "HOME":
                plus2_team = home
                minus2_team = away
            else:
                plus2_team = away
                minus2_team = home

            plus2_total[plus2_team] += 1
            minus2_total[minus2_team] += 1

    FI = {t: 1.0 for t in plus2_total}
    CI = {t: 1.0 for t in minus2_total}

    return plus2_total, FI, minus2_total, CI


# =========================
# KPI 2–3 (REAL) — desde goal_events.csv
# =========================

def plus2_then_equalize_stats_from_goals():
    by_match = defaultdict(list)

    with GOALS_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            by_match[r["match_id"]].append({
                "minute": int(r["minute"]),
                "home_goals": int(r["home_goals"]),
                "away_goals": int(r["away_goals"]),
            })

    match_teams = {}
    with MATCHES_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            match_teams[r["match_id"]] = (r["home"], r["away"])

    plus2_total = defaultdict(int)
    plus2_equalized = defaultdict(int)
    minus2_total = defaultdict(int)
    minus2_equalized = defaultdict(int)

    for match_id, events in by_match.items():
        if match_id not in match_teams:
            continue

        home, away = match_teams[match_id]
        events = sorted(events, key=lambda e: e["minute"])

        seen_plus2 = False
        plus2_side = None
        equalized = False

        for e in events:
            diff = e["home_goals"] - e["away_goals"]

            if not seen_plus2 and abs(diff) >= 2:
                seen_plus2 = True
                plus2_side = "HOME" if diff > 0 else "AWAY"
                continue

            if seen_plus2 and diff == 0:
                equalized = True
                break

        if not seen_plus2:
            continue

        if plus2_side == "HOME":
            team_plus2 = home
            team_minus2 = away
        else:
            team_plus2 = away
            team_minus2 = home

        plus2_total[team_plus2] += 1
        minus2_total[team_minus2] += 1

        if equalized:
            plus2_equalized[team_plus2] += 1
            minus2_equalized[team_minus2] += 1

    return plus2_total, plus2_equalized, minus2_total, minus2_equalized


def fi_ci_real_from_goals():
    p2, p2_eq, m2, m2_eq = plus2_then_equalize_stats_from_goals()

    FI = {t: (p2_eq[t] / p2[t]) for t in p2}
    CI = {t: (m2_eq[t] / m2[t]) for t in m2}

    return p2, FI, m2, CI


# =========================
# RANKINGS
# =========================

def top_ranking(d: dict, n: int = 10):
    return sorted(d.items(), key=lambda x: x[1], reverse=True)[:n]


def chaos_score(plus2_total, FI, minus2_total, CI):
    teams = set(plus2_total) | set(minus2_total)
    score = {}

    for t in teams:
        score[t] = (
            FI.get(t, 0.0) * plus2_total.get(t, 0)
            + CI.get(t, 0.0) * minus2_total.get(t, 0)
        )

    return score


# =========================
# FIXTURES FUTUROS
# =========================

def load_fi_ci_tables():
    return fragility_and_comeback_stats()


def score_fixture(home, away, plus2_total, FI, minus2_total, CI):
    base = (FI.get(home, 0) * CI.get(away, 0)) + (FI.get(away, 0) * CI.get(home, 0))
    volume = (
        plus2_total.get(home, 0)
        + minus2_total.get(home, 0)
        + plus2_total.get(away, 0)
        + minus2_total.get(away, 0)
    )
    return base * math.log(1 + volume) if volume > 0 else 0.0


def hot_fixtures(top_n: int = 20):
    plus2_total, FI, minus2_total, CI = load_fi_ci_tables()

    fixtures = []
    with FIXTURES_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            heat = score_fixture(
                r["home"], r["away"],
                plus2_total, FI, minus2_total, CI
            )
            fixtures.append((heat, r["date"], r["league"], r["home"], r["away"]))

    fixtures.sort(reverse=True, key=lambda x: x[0])
    return fixtures[:top_n]


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("Volatility Index (VI) por liga")
    print("-" * 30)
    for lg, v in volatility_index_by_league().items():
        print(f"{lg}: {v:.3f}")

    print("\nFI / CI (básico, solo eventos)")
    print("-" * 30)
    p2, FI, m2, CI = fragility_and_comeback_stats()
    for t in FI:
        print(f"{t}: FI={FI[t]:.3f} | CI={CI.get(t, 0):.3f}")

    print("\nFI / CI REAL (desde goal_events.csv)")
    print("-" * 40)
    p2r, FIr, m2r, CIr = fi_ci_real_from_goals()

    print("\nTop Fragility REAL")
    for t, v in top_ranking(FIr):
        print(f"{t}: FI_real={v:.3f} | +2 casos={p2r.get(t,0)}")

    print("\nTop Comeback REAL")
    for t, v in top_ranking(CIr):
        print(f"{t}: CI_real={v:.3f} | -2 casos={m2r.get(t,0)}")

    print("\nPartidos FUTUROS más 'calientes' (Heat Score)")
    print("-" * 55)
    try:
        for h, d, l, ho, aw in hot_fixtures():
            print(f"{d} {l} | {ho} vs {aw} | heat={h:.3f}")
    except FileNotFoundError:
        print("No existe fixtures.csv todavía")
