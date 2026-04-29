from sqlalchemy import Column, Integer, String, DateTime, Text

from app.db.base import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    bookie = Column(String, nullable=False, index=True)
    competicion = Column(String, nullable=False, index=True)
    partido = Column(String, nullable=False, index=True)
    mercados = Column(String, nullable=False)
    deporte = Column(String, nullable=False, index=True)

    source = Column(String, nullable=True, index=True)
    external_id = Column(String, nullable=True, index=True)
    commence_time = Column(DateTime, nullable=True, index=True)

    home_team = Column(String, nullable=True)
    away_team = Column(String, nullable=True)

    # Cuotas reales: JSON con estructura {mercado: {outcome: cuota}}
    cuotas = Column(Text, nullable=True)