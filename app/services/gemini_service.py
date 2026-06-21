from google import genai
from app.core.config import settings
from app.domain.models.ai_prediction import AIPredictionResult, MatchDataPayload
from app.services.fallback_service import DeepSeekFallbackService

class GeminiAnalystService:
    def __init__(self):
        # Configure the Google GenAI SDK
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"
        self.fallback_service = DeepSeekFallbackService()
        
        self.system_instruction = """
Eres el motor algorítmico principal de ApexTip AI, un sistema de Sports Investing de nivel institucional inspirado en el análisis cuantitativo avanzado. Tu objetivo es encontrar "Value Bets" (apuestas de valor) con cuotas estrictamente superiores a 1.50, maximizando el ROI a largo plazo y apuntando a una tasa de acierto del 80%.

Para cada partido provisto, DEBES evaluar y calcular:
1. APEX VELOCITY (Fuerza del equipo): Métrica del 1 al 100 basada en xG (Goles Esperados), rachas de victorias, rendimiento de local/visitante y bajas críticas.
2. FILTRO ANTI-TRAMPA DE LAS VEGAS: Compara la probabilidad real matemática contra la cuota implícita de la casa. Si la casa da muy favorito a un equipo pero su Apex Velocity es bajo, alerta de una posible trampa u oportunidad en el mercado contrario (Underdog de valor).
3. SELECCIÓN DE MERCADO ÓPTIMO: Elige estrictamente SOLO UNO de los siguientes mercados donde la ventaja matemática sea máxima:
   - Más/Menos Goles (Over/Under)
   - Tiros de Esquina (Corners - Altamente valorado analizando volumen ofensivo lateral)
   - Apuesta sin Empate (Draw No Bet / DNB)
   - Doble Oportunidad (1X / X2)
4. NIVEL DE CONFIANZA (ESTRELLAS): Clasifica la jugada de 1 a 5 estrellas:
   - 1-3 Estrellas: Evitar / Riesgo alto / Sin valor.
   - 4 Estrellas: Alta probabilidad, cuota justificada (Value Bet clara).
   - 5 Estrellas: Oportunidad matemática máxima (Inversión Fuerte).

DEBES devolver la respuesta EXCLUSIVAMENTE en formato JSON estructurado, masticado y listo para el usuario de la app móvil. No alucines, sé frío, analítico y matemático.
"""

    async def analyze_match(self, payload: MatchDataPayload) -> AIPredictionResult:
        prompt_contexto = f"""
        ANALIZA EL SIGUIENTE PARTIDO CON LA ESTRATEGIA APEXTIP:
        Partido: {payload.home_team} vs {payload.away_team}
        Cuotas de la Casa: {payload.current_odds}
        
        1. DATA RECIENTE (APEX VELOCITY - ÚLTIMOS 30 DÍAS):
        {payload.apex_velocity_data}
        
        2. CONTEXTO TEMPORADA GENERAL:
        {payload.context_one_year_data}
        
        3. HISTÓRICO PROFUNDO H2H (4 AÑOS):
        {[h2h.model_dump() for h2h in payload.h2h_historic_four_years]}
        """
        try:
            # Usando Structured Outputs de Gemini a través del SDK genai
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_contexto,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': AIPredictionResult, # Pasar la clase Pydantic directamente
                    'system_instruction': self.system_instruction,
                    'temperature': 0.2, # Baja temperatura para análisis lógico y consistente
                },
            )
            
            # El SDK ya devuelve el objeto validado en .parsed si se usó response_schema
            if response.parsed:
                return response.parsed
            else:
                raise ValueError("Gemini returned a response, but parsing failed.")
                
        except Exception as e:
            # Mecanismo de Fallback ante error de conexión o parseo
            print(f"Gemini API Error: {str(e)}. Falling back to DeepSeek...")
            return await self.fallback_service.generate_prediction(prompt_contexto)

gemini_service = GeminiAnalystService()
