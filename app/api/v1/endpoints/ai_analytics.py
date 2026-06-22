from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.gemini_service import gemini_service
from app.services.api_football_service import api_football_service
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client
from app.domain.models.ai_prediction import SportEnum, AIPredictionResult
from supabase import Client

router = APIRouter()

from datetime import datetime, timedelta

@router.get("/predictions")
async def get_ai_predictions(
    date: str,
    tz_offset: int = 0, # Mantenemos el parámetro para no romper el cliente, pero lo ignoramos
    current_user: dict = Depends(get_current_user), 
    db: Client = Depends(get_supabase_client)
):
    """
    Retorna las predicciones pre-calculadas por el Analista IA para una fecha dada.
    """
    # Verificación Premium (opcional)
    if current_user.get("roles", {}).get("subscription") != "premium":
        pass # Permitido temporalmente para desarrollo
        
    try:
        # Filtramos por rango de fechas porque en la base de datos es un Timestamp
        # La BD guarda todo a las 00:00:00Z, así que buscamos el día exacto
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        
        response = db.table("ai_predictions").select("*").gte("event_date", start_date).lte("event_date", end_date).execute()
        data = response.data
        
        # Calcular Resumen de Unidades
        summary = {
            "total_tips": len(data),
            "won": 0,
            "lost": 0,
            "void": 0,
            "pending": 0,
            "total_units_profit": 0.0
        }
        
        for p in data:
            st = p.get("status")
            if st in summary:
                summary[st] += 1
            if p.get("pnl") is not None:
                summary["total_units_profit"] += float(p["pnl"])
                
        # Redondear profit a 2 decimales
        summary["total_units_profit"] = round(summary["total_units_profit"], 2)
                
        return {
            "summary": summary,
            "predictions": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
