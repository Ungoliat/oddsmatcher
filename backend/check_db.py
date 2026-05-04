import sqlite3

conn = sqlite3.connect('oddsmatcher.db')
rows = conn.execute("SELECT bookie, partido, cuotas FROM events WHERE partido LIKE '%Wolverhampton%' OR partido LIKE '%Fulham%' OR partido LIKE '%Wolves%'").fetchall()
for r in rows:
    print(f"BOOKIE: {r[0]}")
    print(f"PARTIDO: {r[1]}")
    print(f"CUOTAS: {r[2]}")
    print("---")