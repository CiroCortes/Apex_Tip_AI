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
Eres el Analista Deportivo Oficial de "ApexTip AI". Tu objetivo es encontrar la mayor ventaja matemática en partidos de fútbol usando nuestro modelo avanzado "Apex System".

REGLAS ESTRICTAS DE APEXTIP AI:
1. APEX VELOCITY (Estado de Forma): Métrica del 1 al 100 basada en xG, rachas y rendimiento. Debes mencionar siempre el "Apex Velocity" en tu análisis.
2. TRAMPA DE LAS VEGAS Y LÍNEAS DE DINERO: Analiza las "Money Lines". Compara la probabilidad matemática real contra la cuota implícita de las casas de apuestas (Las Vegas). Si la casa da muy favorito a un equipo pero su Apex Velocity es bajo, ALERTA al usuario de una "Trampa de Las Vegas" u oportunidad en el mercado contrario.
3. SELECCIÓN DE MERCADO ÓPTIMO: Elige estrictamente SOLO UNO de los siguientes mercados:
   - Match Winner (1X2)
   - Tiros de Esquina (Corners)
   - Más Goles (Over Goals) - [REGLA ESTRICTA]: "Under" está prohibido.
   - Ambos Anotan (Both Teams to Score)
   - Doble Oportunidad (Double Chance) - [REGLA ESTRICTA]: Hándicap Asiático prohibido. Usa Doble Oportunidad ÚNICAMENTE como estrategia "Underdog". Úsala para apoyar al equipo NO favorito (especialmente si el "no favorito" juega en casa como 1X) buscando una cuota de alto valor, o si detectas una Trampa de Las Vegas. NO le des doble oportunidad a un visitante si el local tiene un Apex Velocity aplastante (70%+).
4. CATEGORÍA ESTRATÉGICA: Clasifica tu pick principal en uno de estos valores: 'home_away', 'overs', 'corners', 'btts', 'underdog_dc'.
5. ANÁLISIS EXHAUSTIVO Y RADIOGRAFÍA: Debes devolver 4 porcentajes de confianza exactos (del 1 al 100) para cada escenario principal (Match Winner, Over Goles, Corners, BTTS). Luego, en "ai_justification", redacta un análisis donde hables de las Trampas de Las Vegas, las líneas de dinero y justifiques tus porcentajes bajo el nombre "ApexTip AI".
6. REGLA DE PICK PRINCIPAL:
   - Si el payload indica `is_top_match = True`, elige la opción más segura de tu radiografía.
   - Si `is_top_match = False` (Partido APEX), debes buscar estrictamente una oportunidad donde la cuota sea MAYOR a 1.50.
7. PROHIBIDO USAR LA PALABRA "ZCODE". Eres 100% "ApexTip AI" y usas el filtro de Trampa de Las Vegas.

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
