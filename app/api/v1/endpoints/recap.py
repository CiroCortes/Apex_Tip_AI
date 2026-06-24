from fastapi import APIRouter, Depends, HTTPException
import requests
from datetime import datetime
from app.services.supabase_client import get_supabase_client
from supabase import Client
from app.core.config import settings

router = APIRouter()
SPORTS_API_URL_FIXTURES = "https://v3.football.api-sports.io/fixtures"

@router.post("/run-recap")
async def run_daily_recap(db: Client = Depends(get_supabase_client)):
    """
    Busca todas las predicciones pendientes en Supabase, consulta a API-Sports
    si el partido ya terminó y actualiza el estado (won/lost) calculando el PnL.
    """
    api_key = settings.API_FOOTBALL_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="API_FOOTBALL_KEY no configurada")

    # 1. Traer predicciones pendientes
    response = db.table("ai_predictions").select("*").eq("status", "pending").execute()
    pending_predictions = response.data
    
    if not pending_predictions:
        return {"status": "success", "message": "No hay predicciones pendientes para procesar."}

    headers = {"x-apisports-key": api_key}
    processed_count = 0
    
    for pred in pending_predictions:
        fixture_id = pred["fixture_id"]
        
        # 2. Consultar el estado del partido a API-Football
        fixture_response = requests.get(SPORTS_API_URL_FIXTURES, headers=headers, params={"id": fixture_id})
        
        if fixture_response.status_code != 200:
            continue
            
        data = fixture_response.json().get("response", [])
        if not data:
            continue
            
        match_data = data[0]
        status_short = match_data["fixture"]["status"]["short"]
        
        # FT = Full Time, PEN = Penalties, AET = After Extra Time
        if status_short in ["FT", "PEN", "AET"]:
            goals_home = match_data["goals"]["home"]
            goals_away = match_data["goals"]["away"]
            
            # Lógica básica para determinar si se ganó o se perdió el pronóstico
            # NOTA: En un sistema ZCode avanzado, esto requiere un parser complejo del mercado.
            # Aquí hacemos una validación simplificada para los mercados principales.
            market = pred["selected_market"]
            is_won = False
            
            if "Home" in market or "Local" in market and "Match Winner" in market:
                is_won = goals_home > goals_away
            elif "Away" in market or "Visitante" in market and "Match Winner" in market:
                is_won = goals_away > goals_home
            elif ("Draw" in market or "Empate" in market) and "No Bet" not in market:
                is_won = goals_home == goals_away
            elif "Draw No Bet" in market or "Empate No Acción" in market:
                if goals_home == goals_away:
                    is_won = None # Void
                elif "Home" in market or "Local" in market:
                    is_won = goals_home > goals_away
                else:
                    is_won = goals_away > goals_home
            elif "Double Chance" in market or "Doble Oportunidad" in market:
                if ("Home" in market or "Local" in market) and ("Away" in market or "Visitante" in market):
                    is_won = goals_home != goals_away # 12
                elif ("Home" in market or "Local" in market) and ("Draw" in market or "Empate" in market):
                    is_won = goals_home >= goals_away # 1X
                elif ("Away" in market or "Visitante" in market) and ("Draw" in market or "Empate" in market):
                    is_won = goals_away >= goals_home # X2
            elif ("Over" in market or "Más" in market) and ("Goals" in market or "Goles" in market):
                # Ej: Over 2.5 Goals o Más de 2.5 Goles
                try:
                    threshold_str = [word for word in market.split() if '.' in word or word.isdigit()][0]
                    threshold = float(threshold_str)
                    is_won = (goals_home + goals_away) > threshold
                except:
                    pass
            elif "Corners" in market:
                 # API-Sports no siempre devuelve corners en fixtures si no tienes suscripción Pro,
                 # asumiendo PENDING manual o revisión en un nivel más avanzado.
                 pass

            # Calculamos PnL
            stake = float(pred.get("stake", 1.0))
            quota = float(pred["recommended_quota"])
            
            if is_won is True:
                final_status = "won"
                pnl = (stake * quota) - stake
            elif is_won is False:
                final_status = "lost"
                pnl = -stake
            else:
                final_status = "void"
                pnl = 0.0
                
            # 3. Actualizar la base de datos
            db.table("ai_predictions").update({
                "status": final_status,
                "pnl": pnl,
                "goals_home": goals_home,
                "goals_away": goals_away
            }).eq("id", pred["id"]).execute()
            
            processed_count += 1

    return {
        "status": "success", 
        "message": f"Se procesaron {processed_count} partidos terminados."
    }
