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
    # Verificamos si el usuario es premium
    is_premium_user = current_user.get("roles", {}).get("subscription") == "premium"
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
            
            # CENSURADOR FREEMIUM: Ocultar el tesoro a usuarios Free
            if not is_premium_user and p.get("tier") == "premium":
                p["selected_market"] = "LOCKED_PREMIUM"
                p["recommended_quota"] = 0.0
                p["ai_justification"] = "LOCKED_PREMIUM"
                p["strategy"] = "LOCKED_PREMIUM"
                p["confidence_over"] = 0
                p["confidence_corners"] = 0
                p["confidence_btts"] = 0
                
        # Redondear profit a 2 decimales
        summary["total_units_profit"] = round(summary["total_units_profit"], 2)
                
        return {
            "summary": summary,
            "predictions": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_ai_stats(days: int = 7, db: Client = Depends(get_supabase_client)):
    """
    Retorna el historial de profit agrupado por días y separado por tier (global, free, premium).
    Útil para dibujar gráficos de líneas en aplicaciones móviles.
    """
    try:
        end_date_dt = datetime.utcnow()
        start_date_dt = end_date_dt - timedelta(days=days - 1)
        
        start_date_str = start_date_dt.strftime("%Y-%m-%d") + "T00:00:00Z"
        end_date_str = end_date_dt.strftime("%Y-%m-%d") + "T23:59:59Z"
        
        response = db.table("ai_predictions").select("*").gte("event_date", start_date_str).lte("event_date", end_date_str).execute()
        data = response.data
        
        # Diccionarios para asegurar que todos los días estén presentes (incluso los vacíos)
        global_map = {}
        free_map = {}
        premium_map = {}
        
        for i in range(days):
            day_str = (start_date_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            empty_stats = {"date": day_str, "profit": 0.0, "won": 0, "lost": 0}
            global_map[day_str] = empty_stats.copy()
            free_map[day_str] = empty_stats.copy()
            premium_map[day_str] = empty_stats.copy()
            
        # Llenar con datos reales
        for p in data:
            if not p.get("event_date"):
                continue
                
            day_str = p["event_date"][:10]
            if day_str not in global_map:
                continue
                
            pnl = float(p.get("pnl") or 0.0)
            status = p.get("status")
            tier = p.get("tier", "premium")
            
            # Global
            global_map[day_str]["profit"] += pnl
            if status == "won":
                global_map[day_str]["won"] += 1
            elif status == "lost":
                global_map[day_str]["lost"] += 1
                
            # Por Tier
            target_map = free_map if tier == "free" else premium_map
            target_map[day_str]["profit"] += pnl
            if status == "won":
                target_map[day_str]["won"] += 1
            elif status == "lost":
                target_map[day_str]["lost"] += 1

        # Redondear y formatear a listas
        for m in [global_map, free_map, premium_map]:
            for day in m:
                m[day]["profit"] = round(m[day]["profit"], 2)

        return {
            "global": list(global_map.values()),
            "free": list(free_map.values()),
            "premium": list(premium_map.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
