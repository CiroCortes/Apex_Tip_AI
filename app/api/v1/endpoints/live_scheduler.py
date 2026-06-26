from fastapi import APIRouter, Depends, BackgroundTasks
import requests
from datetime import datetime
from app.services.supabase_client import get_supabase_client
from supabase import Client
from app.core.config import settings
from app.services.live_gemini_service import live_gemini_service
from app.domain.models.live_prediction import LiveMatchPayload
import asyncio

router = APIRouter()

SPORTS_API_URL_LIVE = "https://v3.football.api-sports.io/fixtures?live=all"
SPORTS_API_URL_STATS = "https://v3.football.api-sports.io/fixtures/statistics"
SPORTS_API_URL_ODDS_LIVE = "https://v3.football.api-sports.io/odds/live"

@router.post("/scan-live")
async def scan_live_fixtures(background_tasks: BackgroundTasks, db: Client = Depends(get_supabase_client)):
    """
    Escanea partidos en vivo. Si cumplen la condición de 0-0 en los minutos clave (HT o 55-65),
    busca sus estadísticas y cuotas, y pide a Gemini un análisis.
    Se recomienda correr este CRON cada 1-2 minutos.
    """
    api_key = settings.API_FOOTBALL_KEY
    headers = {"x-apisports-key": api_key}
    
    # 1. Obtener Partidos en Vivo
    response = requests.get(SPORTS_API_URL_LIVE, headers=headers)
    if response.status_code != 200:
        return {"status": "error", "message": "Fallo al conectar con API-Sports (Live)"}
        
    fixtures_data = response.json().get("response", [])
    
    # 2. Filtrar partidos que nos interesan (0-0, y en minutos clave)
    candidates = []
    for f in fixtures_data:
        goals_home = f["goals"]["home"] or 0
        goals_away = f["goals"]["away"] or 0
        status_elapsed = f["fixture"]["status"]["elapsed"]
        
        # Estrategia pura: Solo si van 0-0
        if goals_home == 0 and goals_away == 0:
            # Ventana A: Minuto 20 a 35 (Para Over 0.5 HT)
            # Ventana B: Minuto 55 a 85 (Para Over 1.5 Match / Over 0.5 Match)
            if (20 <= status_elapsed <= 35) or (55 <= status_elapsed <= 85):
                candidates.append(f)
                
    if not candidates:
        return {"status": "success", "message": "Ningún partido cumple con la ventana de tiempo 0-0."}

    # Procesar candidatos en background para no bloquear el CRON
    background_tasks.add_task(process_live_candidates, candidates, headers, db)
    
    return {"status": "success", "message": f"Evaluando {len(candidates)} candidatos en background."}

async def process_live_candidates(candidates: list, headers: dict, db: Client):
    for f in candidates:
        fixture_id = str(f["fixture"]["id"])
        status_elapsed = f["fixture"]["status"]["elapsed"]
        
        # 2.5 Evitar tips duplicados (solo 1 bet por partido en vivo)
        check_resp = db.table("ai_live_predictions").select("id").eq("fixture_id", fixture_id).execute()
        if check_resp.data:
            continue
        
        # 3. Obtener estadísticas del partido
        stats_resp = requests.get(SPORTS_API_URL_STATS, headers=headers, params={"fixture": fixture_id})
        if stats_resp.status_code != 200:
            continue
            
        stats_data = stats_resp.json().get("response", [])
        if not stats_data or len(stats_data) < 2:
            continue
            
        # Parsear stats
        sot_home = sot_away = corners_home = corners_away = 0
        for team_stats in stats_data:
            is_home = str(team_stats["team"]["id"]) == str(f["teams"]["home"]["id"])
            for stat in team_stats["statistics"]:
                val = stat["value"] or 0
                if stat["type"] == "Shots on Goal":
                    if is_home: sot_home = int(val)
                    else: sot_away = int(val)
                elif stat["type"] == "Corner Kicks":
                    if is_home: corners_home = int(val)
                    else: corners_away = int(val)

        # Filtro Matemático Básico: +3 Remates a puerta y +4 Corners en total (o por equipo, ajustamos a total por flexibilidad de la IA)
        total_sot = sot_home + sot_away
        total_corners = corners_home + corners_away
        
        if total_sot < 3 or total_corners < 4:
            continue # No cumple el volumen ofensivo mínimo
            
        # 4. Obtener cuotas en vivo
        odds_resp = requests.get(SPORTS_API_URL_ODDS_LIVE, headers=headers, params={"fixture": fixture_id})
        current_odds_over_05_fh = None
        current_odds_over_15_match = None
        current_odds_over_05_match = None
        
        if odds_resp.status_code == 200:
            odds_data = odds_resp.json().get("response", [])
            if odds_data:
                markets = odds_data[0].get("odds", [])
                for market in markets:
                    # Id 10 = First Half Over/Under, Id 5 = Match Goals Over/Under (Depende de API-sports)
                    if market["id"] == 10: # First Half Over/Under
                        for val in market["values"]:
                            if val["value"] == "Over 0.5": current_odds_over_05_fh = float(val["odd"])
                    elif market["id"] == 5: # Match Goals
                        for val in market["values"]:
                            if val["value"] == "Over 1.5": current_odds_over_15_match = float(val["odd"])
                            if val["value"] == "Over 0.5": current_odds_over_05_match = float(val["odd"])

        # 5. Armar Payload para Gemini
        payload = LiveMatchPayload(
            fixture_id=fixture_id,
            home_team=f["teams"]["home"]["name"],
            away_team=f["teams"]["away"]["name"],
            minute=status_elapsed,
            score="0-0",
            shots_on_target_home=sot_home,
            shots_on_target_away=sot_away,
            corners_home=corners_home,
            corners_away=corners_away,
            current_odds_over_05_fh=current_odds_over_05_fh,
            current_odds_over_15_match=current_odds_over_15_match,
            current_odds_over_05_match=current_odds_over_05_match,
            is_top_match=True # Por ahora tratamos a todos como top para que busque
        )
        
        try:
            prediction = await live_gemini_service.analyze_live_match(payload)
            
            # Solo guardamos si la IA aprueba con alta confianza (ej. >= 80)
            if prediction.confidence >= 80:
                db_record = {
                    "fixture_id": fixture_id,
                    "event_name": f"{payload.home_team} vs {payload.away_team}",
                    "minute": payload.minute,
                    "selected_market": prediction.selected_market,
                    "recommended_quota": prediction.recommended_quota,
                    "confidence": prediction.confidence,
                    "ai_justification": prediction.ai_justification,
                    "timestamp": datetime.utcnow().isoformat()
                }
                # Insertar en tabla nueva
                db.table("ai_live_predictions").insert(db_record).execute()
                print(f"🔥 LIVE TIP GUARDADO: {db_record['event_name']} | {db_record['selected_market']} @ {db_record['recommended_quota']}")
                
            await asyncio.sleep(2) # Respetar rate limits
        except Exception as e:
            print(f"Error procesando {fixture_id} en vivo: {e}")
