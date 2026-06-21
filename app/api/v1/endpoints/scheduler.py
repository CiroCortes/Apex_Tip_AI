from fastapi import APIRouter, Depends, HTTPException
import os
import requests
from datetime import datetime, timedelta
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
async def scan_and_predict_pre_match(date: str = None, db: Client = Depends(get_supabase_client)):
    """
    Escanea partidos usando una ventana deslizante de 6 días (si no se envía fecha).
    Filtra los que ya están en base de datos para no gastar IA.
    """
    if date:
        dates_to_scan = [date]
    else:
        dates_to_scan = [(datetime.utcnow() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6)]

    api_key = settings.API_FOOTBALL_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="API_FOOTBALL_KEY no configurada")
        
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    # Obtener fixtures ya analizados para ignorarlos
    try:
        existing = db.table("ai_predictions").select("fixture_id").execute()
        existing_ids = {str(r["fixture_id"]) for r in existing.data}
    except:
        existing_ids = set()

    oportunidades = []

    for scan_date in dates_to_scan:
        print(f"🔍 Escaneando fecha: {scan_date}...")
        
        # 1. Traer fixtures para obtener nombres y estados
        fixtures_response = requests.get(SPORTS_API_URL_FIXTURES, headers=headers, params={"date": scan_date})
        if fixtures_response.status_code != 200:
            continue
            
        fixtures_data = fixtures_response.json().get("response", [])
        if not fixtures_data:
            continue
            
        team_names_map = {}
        for f in fixtures_data:
            team_names_map[str(f["fixture"]["id"])] = {
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "league": f["league"]["name"],
                "league_id": f["league"]["id"],
                "status": f["fixture"]["status"]["short"]
            }

        # 2. Traer cuotas
        odds_data = []
        current_page = 1
        total_pages = 1
        
        while current_page <= total_pages:
            odds_response = requests.get(SPORTS_API_URL_ODDS, headers=headers, params={"date": scan_date, "bookmaker": "1", "page": current_page})
            if odds_response.status_code != 200:
                break
            json_resp = odds_response.json()
            odds_data.extend(json_resp.get("response", []))
            total_pages = json_resp.get("paging", {}).get("total", 1)
            current_page += 1
            
        print(f"✅ Cuotas de {len(odds_data)} partidos para {scan_date}.")
        
        for item in odds_data:
            fixture_id = str(item["fixture"]["id"])
            
            # Si ya lo analizamos antes, lo saltamos
            if fixture_id in existing_ids:
                continue
                
            if not item.get("bookmakers"):
                continue
                
            bookmaker = item["bookmakers"][0]
            team_info = team_names_map.get(fixture_id, {"home": "Local", "away": "Visitante", "league": "Unknown", "league_id": 0, "status": "Unknown"})
            
            # Solo predecir si NO han comenzado
            if team_info["status"] != "NS":
                continue
                
            is_top_match = team_info["league_id"] in [1, 2, 3, 4, 9, 39, 61, 78, 135, 140, 253]
            allowed_markets = ["Match Winner", "Goals Over/Under", "Corners", "Both Teams Score", "Double Chance"]
            filtered_odds = {}
            has_value_bet = False
            
            for bet in bookmaker["bets"]:
                if bet["name"] not in allowed_markets:
                    continue
                for v in bet["values"]:
                    odd_val = float(v["odd"])
                    val_name = str(v["value"])
                    if "Under" in val_name and bet["name"] == "Goals Over/Under":
                        continue
                    filtered_odds[f"{bet['name']} - {val_name}"] = odd_val
                    if 1.5 <= odd_val <= 3.0:
                        has_value_bet = True
            
            if has_value_bet or is_top_match:
                print(f"⏳ Analizando partido {fixture_id} ({team_info['home']} vs {team_info['away']})...")
                payload = MatchDataPayload(
                    fixture_id=fixture_id,
                    match_date=scan_date,
                    home_team=team_info["home"],
                    away_team=team_info["away"],
                    current_odds=filtered_odds,
                    is_top_match=is_top_match,
                    apex_velocity_data={"last_30_days": "Sample Data"},
                    context_one_year_data={"current_season": "Sample Data"},
                    h2h_historic_four_years=[]
                )
                
                try:
                    prediction = await gemini_service.analyze_match(payload)
                    tier = "premium" if prediction.main_pick_confidence >= 75 else "free"
                    
                    db_record = {
                        "fixture_id": fixture_id,
                        "sport": "football",
                        "league_name": team_info["league"],
                        "event_name": f"{team_info['home']} vs {team_info['away']}",
                        "event_date": f"{scan_date}T00:00:00Z",
                        "stake": 1.0,
                        "tier": tier,
                        "is_top_match": is_top_match,
                        "strategy": prediction.strategy,
                        "apex_velocity_home": prediction.apex_velocity_home,
                        "apex_velocity_away": prediction.apex_velocity_away,
                        "selected_market": prediction.selected_market,
                        "recommended_quota": prediction.recommended_quota,
                        "main_pick_confidence": prediction.main_pick_confidence,
                        "confidence_winner": prediction.confidence_winner,
                        "confidence_over": prediction.confidence_over,
                        "confidence_corners": prediction.confidence_corners,
                        "confidence_btts": prediction.confidence_btts,
                        "ai_justification": prediction.ai_justification,
                        "status": "unconfirmed"
                    }
                    
                    res = db.table("ai_predictions").insert(db_record).execute()
                    oportunidades.append(res.data[0])
                    existing_ids.add(fixture_id) # Para no volver a procesar si hay bugs
                    print(f"⭐ Guardado [unconfirmed]: {prediction.selected_market} | Cuota: {prediction.recommended_quota}")
                    await asyncio.sleep(8)
                except Exception as e:
                    print(f"❌ Error en {fixture_id}: {e}")

    print(f"🎉 Terminado. Value Bets guardadas: {len(oportunidades)}")
    return {"status": "success", "processed_fixtures": len(oportunidades)}

@router.post("/confirm-tips")
async def confirm_pre_match_tips(db: Client = Depends(get_supabase_client)):
    """
    Busca partidos 'unconfirmed' que empiezan en la próxima hora.
    Re-verifica las cuotas simulando confirmación directa por ahora.
    Si la cuota bajó de 1.5 (para APEX), lo anula ('void').
    De lo contrario, lo pasa a 'pending'.
    """
    try:
        now = datetime.utcnow()
        limit_time = now + timedelta(minutes=60) # Partidos en la próxima hora
        
        response = db.table("ai_predictions").select("*").eq("status", "unconfirmed").execute()
        unconfirmed_matches = response.data
        
        confirmed_count = 0
        voided_count = 0
        
        for match in unconfirmed_matches:
            try:
                event_date = datetime.strptime(match["event_date"][:19], "%Y-%m-%dT%H:%M:%S")
            except:
                continue
                
            if event_date <= limit_time:
                # TODO: Implementar llamada real a API-Sports para cuota en vivo
                # Lógica: Si es APEX y la cuota es muy baja (<1.5), void.
                if not match["is_top_match"] and float(match["recommended_quota"]) < 1.50:
                    db.table("ai_predictions").update({"status": "void"}).eq("id", match["id"]).execute()
                    voided_count += 1
                else:
                    db.table("ai_predictions").update({"status": "pending"}).eq("id", match["id"]).execute()
                    confirmed_count += 1
                    
        return {"status": "success", "confirmed": confirmed_count, "voided": voided_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
