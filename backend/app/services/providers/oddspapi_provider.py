import os
from typing import Any, Dict, List
import requests
from dotenv import load_dotenv

load_dotenv()


class OddsPapiProvider:
    def __init__(self):
        self.api_key = os.getenv("ODDSPAPI_API_KEY", "").strip()
        self.base_url = os.getenv("ODDSPAPI_BASE_URL", "https://api.oddspapi.io/v4").rstrip("/")
        self.timeout = int(os.getenv("ODDSPAPI_TIMEOUT", "20"))

        if not self.api_key:
            raise ValueError("Falta ODDSPAPI_API_KEY en el .env")

        self.sports = {
            "soccer": 10,
            "basketball": 11,
            "tennis": 12,
        }

        self.market_map = {
            101: "1X2",
            101902: "DC",
            1010: "OU2.5",
            106: "OU0.5",
            108: "OU1.5",
            1012: "OU3.5",
            1014: "OU4.5",
            104: "BTTS",
        }

        self.bookmakers_allowed = [
            "bet365",
            "betfair-ex",
            "bwin.es",
            "betsson",
        ]

        self.tournaments = {
            "soccer": [8, 17, 23, 34, 35],
            "basketball": [],
            "tennis": [],
        }

    def fetch_participants(self, sport_id: int) -> Dict[int, str]:
        url = f"{self.base_url}/participants"
        params = {"sportId": sport_id, "apiKey": self.api_key}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return {int(k): v for k, v in data.items()}

    def fetch_odds_by_tournament(self, tournament_id: int, bookmaker: str) -> List[Dict]:
        url = f"{self.base_url}/odds-by-tournaments"
        params = {
            "tournamentIds": tournament_id,
            "bookmaker": bookmaker,
            "apiKey": self.api_key,
            "oddsFormat": "decimal",
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_events(self) -> Dict[str, Any]:
        all_events = []
        meta = []

        for sport_name, sport_id in self.sports.items():
            tournament_ids = self.tournaments.get(sport_name, [])
            if not tournament_ids:
                continue

            try:
                participants = self.fetch_participants(sport_id)
            except Exception:
                participants = {}

            for tournament_id in tournament_ids:
                fixtures_map: Dict[str, Dict] = {}

                for bookie_slug in self.bookmakers_allowed:
                    try:
                        fixtures = self.fetch_odds_by_tournament(tournament_id, bookie_slug)
                    except Exception:
                        continue

                    for fixture in fixtures:
                        if not isinstance(fixture, dict):
                            continue

                        fixture_id = fixture.get("fixtureId")
                        if not fixture_id:
                            continue

                        if fixture_id not in fixtures_map:
                            p1_id = fixture.get("participant1Id")
                            p2_id = fixture.get("participant2Id")
                            p1_name = participants.get(p1_id, str(p1_id))
                            p2_name = participants.get(p2_id, str(p2_id))

                            fixtures_map[fixture_id] = {
                                "fixture_id": fixture_id,
                                "sport": sport_name,
                                "tournament_id": tournament_id,
                                "start_time": fixture.get("startTime"),
                                "home_team": p1_name,
                                "away_team": p2_name,
                                "bookmakers": {},
                            }

                        bookie_data = fixture.get("bookmakerOdds", {}).get(bookie_slug, {})
                        if not bookie_data.get("bookmakerIsActive", False):
                            continue

                        markets = bookie_data.get("markets", {})
                        processed_markets = {}

                        for market_id_str, market_data in markets.items():
                            try:
                                market_id = int(market_id_str)
                            except ValueError:
                                continue

                            if market_id not in self.market_map:
                                continue

                            market_label = self.market_map[market_id]
                            outcomes = market_data.get("outcomes", {})
                            processed_outcomes = {}

                            # Mapa de posición para betfair-ex que usa IDs numéricos
                            outcome_position_map = {
                                "1X2": ["home", "draw", "away"],
                                "DC": ["1X", "12", "X2"],
                                "BTTS": ["Yes", "No"],
                                "OU0.5": ["Over", "Under"],
                                "OU1.5": ["Over", "Under"],
                                "OU2.5": ["Over", "Under"],
                                "OU3.5": ["Over", "Under"],
                                "OU4.5": ["Over", "Under"],
                            }

                            outcome_keys = list(outcomes.keys())
                            position_names = outcome_position_map.get(market_label, [])

                            for idx, (outcome_id_str, outcome_data) in enumerate(outcomes.items()):
                                players = outcome_data.get("players", {})
                                player = players.get("0", {})
                                price = player.get("price")
                                raw_name = player.get("bookmakerOutcomeId", outcome_id_str)

                                # Normalizar nombres
                                name_map = {
                                    "home": "home", "away": "away", "draw": "draw",
                                    "homeordraw": "1X", "homeoraway": "12", "draworaway": "X2",
                                    "home-or-draw": "1X", "home-or-away": "12", "draw-or-away": "X2",
                                    "yes": "Yes", "no": "No",
                                    "over": "Over", "under": "Under",
                                }
                                raw_lower = str(raw_name).lower()
                                outcome_name = raw_name
                                for key, val in name_map.items():
                                    if raw_lower.endswith(key) or raw_lower == key:
                                        outcome_name = val
                                        break

                                # Si sigue siendo un ID numérico, usar posición
                                if str(outcome_name).isdigit() and idx < len(position_names):
                                    outcome_name = position_names[idx]

                                if price and price > 1:
                                    processed_outcomes[str(outcome_name)] = price

                            if processed_outcomes:
                                processed_markets[market_label] = processed_outcomes

                        if processed_markets:
                            fixtures_map[fixture_id]["bookmakers"][bookie_slug] = processed_markets

                for fixture_id, fixture_data in fixtures_map.items():
                    if fixture_data["bookmakers"]:
                        all_events.append(fixture_data)

                meta.append({
                    "sport": sport_name,
                    "tournament_id": tournament_id,
                    "fixtures": len(fixtures_map),
                })

        return {
            "provider": "oddspapi",
            "events": all_events,
            "meta": {
                "total_raw_events": len(all_events),
                "tournaments": meta,
            },
        }