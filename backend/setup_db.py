import sys
sys.path.insert(0, ".")

from app.db.database import init_db, get_conn
from app.db.session import engine
from app.db.base import Base

# Importar todos los modelos explícitamente
from app.models.event import Event
from app.models.user import UserPublic

# Inicializar DB base
init_db()

# Crear tablas SQLAlchemy
print("Modelos registrados:", Base.metadata.tables.keys())
Base.metadata.create_all(bind=engine)
print("Tablas SQLAlchemy creadas")

# Verificar tablas
with get_conn() as conn:
    tablas = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tablas existentes:", tablas)

    try:
        conn.execute("ALTER TABLE events ADD COLUMN cuotas TEXT")
        print("Columna cuotas añadida")
    except Exception as e:
        print(f"cuotas: {e}")

    try:
        conn.execute("CREATE TABLE IF NOT EXISTS bets (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, fecha_registro TEXT NOT NULL, notas TEXT, partido TEXT NOT NULL, competicion TEXT, fecha_evento TEXT, outcome TEXT NOT NULL, mercado TEXT, bookie TEXT NOT NULL, back_odds REAL NOT NULL, lay_odds REAL NOT NULL, stake_back REAL NOT NULL, stake_lay REAL NOT NULL, resultado_estimado REAL, resultado_real REAL, estado TEXT NOT NULL DEFAULT 'pendiente', tipo TEXT NOT NULL DEFAULT 'MB')")
        print("Tabla bets creada")
    except Exception as e:
        print(f"bets: {e}")

    conn.commit()

print("DB lista")