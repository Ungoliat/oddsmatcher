import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")


class BetfairProvider:
    def __init__(self):
        self.app_key = os.getenv("BETFAIR_APP_KEY", "").strip()
        self.username = os.getenv("BETFAIR_USERNAME", "").strip()
        self.password = os.getenv("BETFAIR_PASSWORD", "").strip()
        self.session_token = None
        self.login_url = "https://identitysso.betfair.es/api/login"
        self.api_url = "https://api.betfair.com/exchange/betting/json-rpc/v1"

    def login(self) -> bool:
        res = requests.post(
            self.login_url,
            data={"username": self.username, "password": self.password},
            headers={
                "X-Application": self.app_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        data = res.json()
        if data.get("status") == "SUCCESS":
            self.session_token = data.get("token")
            return True
        print(f"❌ Betfair login error: {data}")
        return False

    def get_headers(self):
        return {
            "X-Application": self.app_key,
            "X-Authentication": self.session_token,
            "Content-Type": "application/json",
        }

    def fetch_odds(self):
        if not self.login():
            return []

        try:
            # Obtener mercados
            catalogue_body = [{
                "jsonrpc": "2.0",
                "method": "SportsAPING/v1.0/listMarketCatalogue",
                "params": {
                    "filter": {
                        "eventTypeIds": ["1"],
                        "marketCountries": ["ES", "GB", "DE", "FR", "IT"],
                        "marketTypeCodes": ["MATCH_ODDS"],
                    },
                    "marketProjection": ["EVENT", "RUNNER_DESCRIPTION", "COMPETITION"],
                    "maxResults": 200,
                },
                "id": 1,
            }]

            res = requests.post(self.api_url, json=catalogue_body, headers=self.get_headers())
            markets = res.json()[0].get("result", [])

            if not markets:
                return []

            market_ids = [m["marketId"] for m in markets]
            market_info = {m["marketId"]: m for m in markets}

            results = []

            # Procesar en lotes de 40
            for i in range(0, len(market_ids), 40):
                batch = market_ids[i:i+40]

                book_body = [{
                    "jsonrpc": "2.0",
                    "method": "SportsAPING/v1.0/listMarketBook",
                    "params": {
                        "marketIds": batch,
                        "priceProjection": {
                            "priceData": ["EX_BEST_OFFERS"],
                            "exBestOffersOverrides": {
                                "bestPricesDepth": 1,
                            },
                        },
                    },
                    "id": 1,
                }]

                res2 = requests.post(self.api_url, json=book_body, headers=self.get_headers())
                books = res2.json()[0].get("result", [])

                for book in books:
                    market_id = book.get("marketId")
                    info = market_info.get(market_id, {})
                    event = info.get("event", {})
                    competition = info.get("competition", {})
                    runners = info.get("runners", [])

                    runner_map = {r["selectionId"]: r["runnerName"] for r in runners}
                    partido = event.get("name", "")
                    competicion = competition.get("name", "")

                    odds = {}
                    for runner in book.get("runners", []):
                        selection_id = runner.get("selectionId")
                        name = runner_map.get(selection_id, str(selection_id))

                        # Normalizar nombre
                        if name == "The Draw":
                            name = "draw"
                        
                        back = runner.get("ex", {}).get("availableToBack", [])
                        lay = runner.get("ex", {}).get("availableToLay", [])
                        back_price = back[0]["price"] if back and back[0].get("size", 0) >= 10 else None
                        lay_price = lay[0]["price"] if lay and lay[0].get("size", 0) >= 10 else None
                        if partido and "Lens" in partido:
                            print(f"🔍 LENS back: {back} lay: {lay}")

                        if back_price:
                            odds[f"back_{name}"] = back_price
                        if lay_price:
                            odds[f"lay_{name}"] = lay_price

                    has_liquidity = any(k.startswith("lay_") for k in odds)
                    if odds and partido and has_liquidity:
                        results.append({
                            "market_id": market_id,
                            "partido": partido,
                            "competicion": competicion,
                            "odds": odds,
                        })

            return results

        except Exception as e:
            print(f"❌ Betfair fetch error: {e}")
            return []