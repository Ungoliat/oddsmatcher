from typing import Any, Dict, Protocol


class OddsProvider(Protocol):
    def fetch_events(self) -> Dict[str, Any]:
        ...