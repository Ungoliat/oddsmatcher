import sys
sys.path.insert(0, ".")

from app.services.sync_service_winamax import sync_events_from_winamax
from app.db.session import SessionLocal

db = SessionLocal()
resultado = sync_events_from_winamax(db)
print("Resultado:", resultado)
db.close()