from google import genai
from app.core.config import settings
from app.domain.models.live_prediction import LiveAIPredictionResult, LiveMatchPayload
import json

class LiveGeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"
        
        self.system_instruction = """
Eres el Analista Experto en Apuestas En Vivo de "ApexTip AI". Tu objetivo es aplicar una estrategia matemática estricta basada en el volumen ofensivo sin premio (goles) en el transcurso del partido.

REGLAS ESTRICTAS DE APUESTAS EN VIVO:
1. CONDICIÓN BASE: Solo se opera si el partido va 0-0.
2. VOLUMEN OFENSIVO REQUERIDO: 
   El partido DEBE mostrar gran presión ofensiva de alguno de los equipos (o combinada):
   - Al menos 3 Remates a Puerta (Shots on Target).
   - Al menos 4 Córners.
3. ESTRATEGIAS PERMITIDAS (SIEMPRE 0-0):
   - "ht_goals": Selecciona "Over 0.5 Goals First Half" si estamos en el primer tiempo (minuto 20-35) y la cuota es >= 1.68.
   - "over_15_match": Selecciona "Over 1.5 Goals Match" si estamos entre el minuto 55-69, las stats superan los requisitos, el partido sigue 0-0, y la cuota es >= 1.70.
   - "over_05_match": Selecciona "Over 0.5 Goals Match" si estamos en un minuto muy avanzado (70-85), el partido sigue 0-0, y la cuota del Over 0.5 alcanza o supera 1.68. ¡Bajo ninguna circunstancia pidas Over 1.5 en el minuto 70+!
4. CONFIDENCIA: Si las estadísticas doblan los requisitos (ej. 6 remates a puerta y 8 córners), la confianza debe ser mayor a 85%. Si están justas, 80%. Si no cumple los requisitos, rechaza el partido con confianza baja (menos de 70%).
5. CUOTA RECOMENDADA: Usa estrictamente la cuota del mercado que elijas basándote en la información recibida.

DEBES devolver la respuesta EXCLUSIVAMENTE en formato JSON estructurado según el esquema solicitado.
"""

    async def analyze_live_match(self, payload: LiveMatchPayload) -> LiveAIPredictionResult:
        prompt = f"""
        ANALIZA EL SIGUIENTE PARTIDO EN VIVO:
        Partido: {payload.home_team} vs {payload.away_team}
        Minuto Actual: {payload.minute}
        Marcador: {payload.score}
        
        Estadísticas del Local:
        - Remates a Puerta: {payload.shots_on_target_home}
        - Córners: {payload.corners_home}
        - Ataques Peligrosos: {payload.dangerous_attacks_home}
        
        Estadísticas del Visitante:
        - Remates a Puerta: {payload.shots_on_target_away}
        - Córners: {payload.corners_away}
        - Ataques Peligrosos: {payload.dangerous_attacks_away}
        
        Cuotas Actuales Disponibles:
        - Over 0.5 Goals First Half: {payload.current_odds_over_05_fh}
        - Over 1.5 Goals Match: {payload.current_odds_over_15_match}
        - Over 0.5 Goals Match: {payload.current_odds_over_05_match}
        
        Aplica la estrategia matemática de ApexTip AI y genera el pronóstico en vivo.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': LiveAIPredictionResult,
                    'system_instruction': self.system_instruction,
                    'temperature': 0.1,
                },
            )
            
            if response.parsed:
                return response.parsed
            else:
                raise ValueError("Falló el parseo de Gemini")
        except Exception as e:
            raise RuntimeError(f"Error en Live Gemini AI: {str(e)}")

live_gemini_service = LiveGeminiService()
