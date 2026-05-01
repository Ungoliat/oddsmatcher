import sys
sys.path.insert(0, ".")
from app.services.providers.betfair_provider import BetfairProvider

provider = BetfairProvider()
results = provider.fetch_odds()

print(f"Total mercados: {len(results)}")
if results:
    print("\nPrimeros 3 resultados:")
    for r in results[:3]:
        print(f"\n{r['competicion']} — {r['partido']}")
        for k, v in r['odds'].items():
            print(f"  {k}: {v}")