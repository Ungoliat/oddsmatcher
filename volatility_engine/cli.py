# volatility_engine/cli.py
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from volatility_engine.storage_csv import read_goal_events, append_match
from volatility_engine.logic import detect_plus2_equalize


GOAL_EVENTS_PATH = Path("volatility_engine/data/goal_events.csv")
MATCHES_PATH = Path("volatility_engine/data/matches_volatility.csv")

HEADER = [
    "match_id","date","league","home","away",
    "final_home_goals","final_away_goals","had_event",
    "minute_plus2","score_at_plus2","side_with_plus2",
    "minute_equalized","score_at_equalized"
]


def main() -> None:
    events = read_goal_events(GOAL_EVENTS_PATH)

    by_match = defaultdict(list)
    for e in events:
        by_match[e.match_id].append(e)

    total = 0
    hits = 0

    for match_id in sorted(by_match.keys()):
        total += 1
        evs = by_match[match_id]
        evt = detect_plus2_equalize(match_id, evs)

        had_event = evt is not None
        if had_event:
            hits += 1
            print(
                f"{match_id}: had_event=True | "
                f"+2@{evt.minute_plus2} ({evt.score_at_plus2}, {evt.side_with_plus2}) -> "
                f"=@{evt.minute_equalized} ({evt.score_at_equalized})"
            )
        else:
            print(f"{match_id}: had_event=False")

        # ⚠️ por ahora datos mockeados (luego los rellenamos reales)
        last = evs[-1]

        if evt is None:
            row = [
                match_id, "2026-01-01", "EPL", "HOME_TEAM", "AWAY_TEAM",
                last.home_goals, last.away_goals, 0,
                "", "", "",
                "", ""
            ]
        else:
            row = [
                match_id, "2026-01-01", "EPL", "HOME_TEAM", "AWAY_TEAM",
                last.home_goals, last.away_goals, 1,
                evt.minute_plus2, evt.score_at_plus2, evt.side_with_plus2,
                evt.minute_equalized, evt.score_at_equalized
            ]

        append_match(MATCHES_PATH, row=row, header=HEADER)


    print("-" * 60)
    print(f"TOTAL partidos analizados: {total}")
    print(f"TOTAL con evento +2->igualdad: {hits}")
    print(f"Ratio: {hits}/{total} = {hits/total:.3f}")
if __name__ == "__main__":
    main()
