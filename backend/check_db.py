import sqlite3

conn = sqlite3.connect('oddsmatcher.db')

print("=== BETFAIR - TODOS LOS EVENTOS ===")
rows = conn.execute("SELECT partido, cuotas FROM events WHERE bookie='betfair' ORDER BY partido").fetchall()
for r in rows:
    print(f"PARTIDO: {r[0]}")
    print(f"CUOTAS: {r[1]}")
    print("---")
