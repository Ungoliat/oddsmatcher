import requests

API_KEY = "18100dfcc521548874bd431d806343ec"
url = "https://api.the-odds-api.com/v4/sports/soccer_spain_la_liga/odds/"

response = requests.get(url, params={
    "apiKey": API_KEY,
    "regions": "eu"
})

data = response.json()

casas = set()
for partido in data:
    for bookie in partido.get("bookmakers", []):
        casas.add(bookie["title"])

print(f"Total casas: {len(casas)}")
for casa in sorted(casas):
    print(f"  - {casa}")