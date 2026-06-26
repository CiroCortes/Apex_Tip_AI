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

import time

# Caché en memoria para evitar saturar Supabase con miles de usuarios concurrentes
PREDICTIONS_CACHE = {}
LIVE_PREDICTIONS_CACHE = {}
CACHE_TTL = 300  # 5 minutos
LIVE_CACHE_TTL = 30 # 30 segundos para en vivo

@router.get("/predictions")
def get_ai_predictions(
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
    
    # 0. Verificamos la Caché antes de ir a Supabase
    cache_key = f"{date}_{tz_offset}_{is_premium_user}"
    current_time = time.time()
    
    if cache_key in PREDICTIONS_CACHE:
        cached_data, timestamp = PREDICTIONS_CACHE[cache_key]
        if current_time - timestamp < CACHE_TTL:
            return cached_data

    try:
        # 1. Parseamos la fecha solicitada por el usuario en su zona local
        local_date = datetime.strptime(date, "%Y-%m-%d")
        
        # 2. Calculamos los rangos en UTC.
        # NOTA: Asumimos que tz_offset viene en minutos (ej. -240 para UTC-4).
        # UTC = Local - offset. Si el frontend usa getTimezoneOffset() de JS (que envía 240 para UTC-4),
        # puede que necesites cambiar la resta por una suma, pero este es el estándar.
        utc_start_dt = local_date - timedelta(minutes=tz_offset)
        utc_end_dt = utc_start_dt + timedelta(days=1) - timedelta(seconds=1)
        
        start_date = utc_start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date = utc_end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        
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
                
        final_response = {
            "summary": summary,
            "predictions": data
        }
        
        # Guardamos en caché por 5 minutos
        PREDICTIONS_CACHE[cache_key] = (final_response, current_time)
        
        return final_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def get_ai_stats(days: int = 7, db: Client = Depends(get_supabase_client)):
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

@router.get("/live-predictions")
def get_live_predictions(
    current_user: dict = Depends(get_current_user), 
    db: Client = Depends(get_supabase_client)
):
    """
    Retorna los picks en vivo generados por el bot In-Play xG.
    """
    is_premium_user = current_user.get("roles", {}).get("subscription") == "premium"
    
    # Caché rápida de 30 segundos
    cache_key = f"live_{is_premium_user}"
    current_time = time.time()
    
    if cache_key in LIVE_PREDICTIONS_CACHE:
        cached_data, timestamp = LIVE_PREDICTIONS_CACHE[cache_key]
        if current_time - timestamp < LIVE_CACHE_TTL:
            return cached_data

    try:
        # Traer predicciones de las últimas 2 horas (para que no salgan picks de ayer)
        time_threshold = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        
        response = db.table("ai_live_predictions").select("*").gte("timestamp", time_threshold).execute()
        data = response.data
        
        for p in data:
            if not is_premium_user:
                p["ai_justification"] = "LOCKED_PREMIUM"
                p["recommended_quota"] = 0.0
                
        final_response = {"live_predictions": data}
        LIVE_PREDICTIONS_CACHE[cache_key] = (final_response, current_time)
        return final_response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

