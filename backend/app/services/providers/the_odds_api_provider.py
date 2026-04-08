import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()


class TheOddsApiProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("THE_ODDS_API_KEY", "").strip()
        self.base_url = os.getenv("THE_ODDS_API_BASE_URL", "https://api.the-odds-api.com/v4").rstrip("/")
        self.regions = os.getenv("THE_ODDS_API_REGIONS", "eu").strip()
        self.markets = os.getenv("THE_ODDS_API_MARKETS", "h2h").strip()
        self.odds_format = os.getenv("THE_ODDS_API_ODDS_FORMAT", "decimal").strip()
        self.date_format = os.getenv("THE_ODDS_API_DATE_FORMAT", "iso").strip()
        self.timeout = int(os.getenv("THE_ODDS_API_TIMEOUT", "20"))

        sports_raw = os.getenv("THE_ODDS_API_SPORTS", "")
        self.sports = [s.strip() for s in sports_raw.split(",") if s.strip()]

        if not self.api_key:
            raise ValueError("Falta THE_ODDS_API_KEY en el .env")

        if not self.sports:
            raise ValueError("Falta THE_ODDS_API_SPORTS en el .env")

    def fetch_events(self) -> Dict[str, Any]:
        all_events: List[Dict[str, Any]] = []
        requests_meta: List[Dict[str, Any]] = []

        for sport_key in self.sports:
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": self.markets,
                "oddsFormat": self.odds_format,
                "dateFormat": self.date_format,
            }

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, list):
                raise ValueError(f"Respuesta inesperada para sport {sport_key}: {type(data)}")

            all_events.extend(data)

            requests_meta.append(
                {
                    "sport_key": sport_key,
                    "status_code": response.status_code,
                    "x_requests_remaining": response.headers.get("x-requests-remaining"),
                    "x_requests_used": response.headers.get("x-requests-used"),
                    "x_requests_last": response.headers.get("x-requests-last"),
                    "events_returned": len(data),
                }
            )

        return {
            "provider": "the_odds_api",
            "events": all_events,
            "meta": {
                "sports": self.sports,
                "regions": self.regions,
                "markets": self.markets,
                "requests": requests_meta,
                "total_raw_events": len(all_events),
            },
        }