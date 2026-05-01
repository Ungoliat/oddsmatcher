import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

username = os.getenv("BETFAIR_USERNAME")
password = os.getenv("BETFAIR_PASSWORD")
app_key = os.getenv("BETFAIR_APP_KEY")

# Login
response = requests.post(
    "https://identitysso.betfair.es/api/login",
    data={"username": username, "password": password},
    headers={
        "X-Application": app_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    },
)
token = response.json()["token"]
print(f"✅ Login OK")

headers = {
    "X-Application": app_key,
    "X-Authentication": token,
    "Content-Type": "application/json",
}

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
        "maxResults": 3,
    },
    "id": 1,
}]

res = requests.post("https://api.betfair.com/exchange/betting/json-rpc/v1", json=catalogue_body, headers=headers)
markets = res.json()[0]["result"]
market_ids = [m["marketId"] for m in markets]
print(f"Mercados: {[m['event']['name'] for m in markets]}")

# Obtener cuotas de back y lay
book_body = [{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listMarketBook",
    "params": {
        "marketIds": market_ids,
        "priceProjection": {
            "priceData": ["EX_BEST_OFFERS"],
            "exBestOffersOverrides": {
                "bestPricesDepth": 1,
            },
        },
    },
    "id": 1,
}]

res2 = requests.post("https://api.betfair.com/exchange/betting/json-rpc/v1", json=book_body, headers=headers)
books = res2.json()[0]["result"]

for book, market in zip(books, markets):
    print(f"\n--- {market['event']['name']} ---")
    runner_map = {r["selectionId"]: r["runnerName"] for r in market["runners"]}
    for runner in book["runners"]:
        name = runner_map.get(runner["selectionId"], "?")
        back = runner["ex"]["availableToBack"]
        lay = runner["ex"]["availableToLay"]
        back_price = back[0]["price"] if back else None
        lay_price = lay[0]["price"] if lay else None
        print(f"  {name}: back={back_price} lay={lay_price}")