from fastapi import APIRouter, Depends
from app.services.volatility_service import get_volatility_dashboard

router = APIRouter(prefix="/volatility", tags=["volatility"])


@router.get("/dashboard")
def dashboard():
    """
    Devuelve KPIs y rankings en JSON para el frontend.
    """
    return get_volatility_dashboard()
