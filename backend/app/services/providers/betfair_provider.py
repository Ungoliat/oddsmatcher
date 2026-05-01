import os
import betfairlightweight
from betfairlightweight import filters
from dotenv import load_dotenv

load_dotenv()

CERTS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "certs")
)


class BetfairProvider:
    def __init__(self):
        self.app_key = os.getenv("BETFAIR_APP_KEY", "").strip()
        self.username = os.getenv("BETFAIR_USERNAME", "").strip()
        self.password = os.getenv("BETFAIR_PASSWORD", "").strip()

    def fetch_odds(self):
        try:
            client = betfairlightweight.APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                certs=CERTS_PATH,
                locale="spain",
            )
            client.login()

            market_filter = filters.market_filter(
                event_type_ids=["1"],
                market_countries=["ES", "GB", "DE", "FR", "IT"],
                market_type_codes=["MATCH_ODDS"],
            )

            markets = client.betting.list_market_catalogue(
                filter=market_filter,
                market_projection=["EVENT", "RUNNER_DESCRIPTION", "COMPETITION"],
                max_results=200,
            )

            market_ids = [m.market_id for m in markets]
            results = []

            for i in range(0, len(market_ids), 40):
                batch = market_ids[i:i+40]
                books = client.betting.list_market_book(
                    market_ids=batch,
                    price_projection=filters.price_projection(
                        price_data=["EX_BEST_OFFERS"]
                    ),
                )

                market_info = {m.market_id: m for m in markets}

                for book in books:
                    info = market_info.get(book.market_id)
                    if not info:
                        continue

                    event_name = info.event.name if info.event else ""
                    competition = info.competition.name if info.competition else ""
                    runner_map = {r.selection_id: r.runner_name for r in info.runners}

                    odds = {}
                    for runner in book.runners:
                        name = runner_map.get(runner.selection_id, str(runner.selection_id))
                        back = runner.ex.available_to_back
                        lay = runner.ex.available_to_lay
                        if back:
                            odds[f"back_{name}"] = back[0].price
                        if lay:
                            odds[f"lay_{name}"] = lay[0].price

                    if odds and event_name:
                        results.append({
                            "market_id": book.market_id,
                            "partido": event_name,
                            "competition": competition,
                            "odds": odds,
                        })

            return results

        except Exception as e:
            print(f"❌ Betfair error: {e}")
            return []