import sqlite3
conn = sqlite3.connect('oddsmatcher.db')
conn.execute("""
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        fecha_registro TEXT NOT NULL,
        notas TEXT,
        partido TEXT NOT NULL,
        competicion TEXT,
        fecha_evento TEXT,
        outcome TEXT NOT NULL,
        mercado TEXT,
        bookie TEXT NOT NULL,
        back_odds REAL NOT NULL,
        lay_odds REAL NOT NULL,
        stake_back REAL NOT NULL,
        stake_lay REAL NOT NULL,
        resultado_estimado REAL,
        resultado_real REAL,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        tipo TEXT NOT NULL DEFAULT 'MB'
    )
""")
conn.commit()
conn.close()
print('OK')