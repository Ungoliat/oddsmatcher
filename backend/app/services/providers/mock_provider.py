from typing import Any

from app.services.providers.base import OddsProvider


class MockOddsProvider(OddsProvider):
    def fetch_events(self) -> list[dict[str, Any]]:
        return [
            {
                "bookie": "bet365",
                "competicion": "Premier League",
                "partido": "Arsenal vs Chelsea",
                "deporte": "football",
                "mercados": ["1X2", "BTTS", "OU"],
            },
            {
                "bookie": "bwin",
                "competicion": "LaLiga",
                "partido": "Real Madrid vs Sevilla",
                "deporte": "football",
                "mercados": ["1X2", "OU"],
            },
        ]