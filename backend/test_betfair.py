import sys
sys.path.insert(0, ".")

from app.services.providers.betfair_provider import BetfairProvider

provider = BetfairProvider()
results = provider.fetch_odds()

print(f"Total mercados: {len(results)}")
if results:
    print("Primer resultado:")
    print(results[0])