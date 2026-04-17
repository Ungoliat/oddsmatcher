from sqlalchemy import Column, Integer, String, DateTime

from app.db.base import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    # Campos legacy / UI actual
    bookie = Column(String, nullable=False, index=True)
    competicion = Column(String, nullable=False, index=True)
    partido = Column(String, nullable=False, index=True)
    mercados = Column(String, nullable=False)
    deporte = Column(String, nullable=False, index=True)

    # Nuevos campos para proveedor real
    source = Column(String, nullable=True, index=True)
    external_id = Column(String, nullable=True, index=True)
    commence_time = Column(DateTime, nullable=True, index=True)

    # Opcionales para siguiente fase
    home_team = Column(String, nullable=True)
    away_team = Column(String, nullable=True)