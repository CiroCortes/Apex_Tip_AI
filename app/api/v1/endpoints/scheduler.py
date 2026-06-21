from fastapi import APIRouter, Depends, HTTPException
import os
import requests
from datetime import datetime
from app.services.gemini_service import gemini_service
from app.domain.models.ai_prediction import MatchDataPayload, H2HHistory
from app.services.supabase_client import get_supabase_client
from supabase import Client
import asyncio

router = APIRouter()

SPORTS_API_URL_ODDS = "https://v3.football.api-sports.io/odds"
SPORTS_API_URL_FIXTURES = "https://v3.football.api-sports.io/fixtures"

from app.core.config import settings

@router.post("/scan-value-bets")
async def scan_and_predict_pre_match(date: str, db: Client = Depends(get_supabase_client)):
    """
    Filtra los partidos del día con cuotas > 1.5 y genera predicciones con IA de forma masiva
    para guardarlas en Supabase antes de que los usuarios abran la app.
    """
    api_key = settings.API_FOOTBALL_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="API_FOOTBALL_KEY no configurada en el .env")

    headers = {"x-apisports-key": api_key}
    
    # 1. Traer TODOS los nombres de los equipos de ese día (1 sola llamada a la API)
    fixtures_response = requests.get(SPORTS_API_URL_FIXTURES, headers=headers, params={"date": date})
    fixtures_data = fixtures_response.json().get("response", [])
    
    # Creamos un diccionario en memoria para buscar rápido: { "1493548": {"home": "Real Madrid", "away": "Barcelona"} }
    team_names_map = {}
    for f in fixtures_data:
        f_id = str(f["fixture"]["id"])
        team_names_map[f_id] = {
            "home": f["teams"]["home"]["name"],
            "away": f["teams"]["away"]["name"]
        }

    # 2. Traer TODAS las cuotas de ese día (1 sola llamada a la API)
    params_odds = {"date": date, "bookmaker": "1"} # 1 suele ser 10Bet o bet365
    odds_response = requests.get(SPORTS_API_URL_ODDS, headers=headers, params=params_odds)
    
    if odds_response.status_code != 200:
        return {"error": f"No se pudieron obtener las cuotas externas: {odds_response.text}"}
        
    odds_data = odds_response.json().get("response", [])
    oportunidades = []

    print(f"✅ Se encontraron {len(odds_data)} partidos con cuotas para el {date}. Iniciando Filtro de Inversión ZCode...")
    
    for item in odds_data:
        fixture_id = str(item["fixture"]["id"])
        
        if not item.get("bookmakers"):
            continue
            
        bookmaker = item["bookmakers"][0]
        bets = bookmaker["bets"][0] 
        
        # Encontrar si al menos una cuota vale la pena
        has_value_bet = any(1.5 <= float(v["odd"]) <= 3.0 for v in bets["values"])
        
        if has_value_bet:
            # Buscar los nombres reales en nuestro diccionario en memoria
            team_info = team_names_map.get(fixture_id, {"home": "Equipo Local", "away": "Equipo Visitante"})
            home_team_name = team_info["home"]
            away_team_name = team_info["away"]
            
            print(f"⏳ Analizando partido {fixture_id} ({home_team_name} vs {away_team_name}) con IA...")
            
            # Empaquetamos todas las cuotas disponibles para que la IA decida la mejor
            all_odds = {v["value"]: float(v["odd"]) for v in bets["values"]}
            
            # Data estructurada con nombres reales
            payload = MatchDataPayload(
                fixture_id=fixture_id,
                match_date=date,
                home_team=home_team_name, 
                away_team=away_team_name,
                current_odds={"market": bets['name'], "available_odds": all_odds},
                apex_velocity_data={"xg_ratio": 1.5, "win_streak": 3, "key_injuries": 0},
                context_one_year_data={"avg_goals": 2.5, "home_win_rate": 0.6},
                h2h_historic_four_years=[]
            )
            
            try:
                prediction = await gemini_service.analyze_match(payload)
                
                db_record = {
                    "fixture_id": fixture_id,
                    "sport": "football",
                    "event_name": f"{home_team_name} vs {away_team_name}",
                    "event_date": f"{date}T00:00:00Z",
                    "apex_velocity_home": prediction.apex_velocity_home,
                    "apex_velocity_away": prediction.apex_velocity_away,
                    "selected_market": prediction.selected_market,
                    "recommended_quota": prediction.recommended_quota,
                    "stars_confidence": prediction.stars_confidence,
                    "ai_justification": prediction.ai_justification,
                    "status": "pending"
                }
                
                # Usamos upsert especificando que el conflicto es en fixture_id
                db.table("ai_predictions").upsert(db_record, on_conflict="fixture_id").execute()
                oportunidades.append(db_record)
                
                print(f"⭐ ¡Predicción guardada! Mercado: {prediction.selected_market} | Cuota: {prediction.recommended_quota}")
                
                # Respetar Rate Limit de Gemini (Aumentado a 8 segundos para evitar límite de la capa gratuita)
                await asyncio.sleep(8)
            except Exception as e:
                print(f"❌ Error procesando {fixture_id}: {e}")

    print(f"🎉 Proceso Cron Terminado. Total de Value Bets guardadas: {len(oportunidades)}")
    return {"status": "success", "processed_fixtures": len(oportunidades)}
