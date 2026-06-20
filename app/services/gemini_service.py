from google import genai
from app.core.config import settings
from app.domain.models.ai_prediction import AIPredictionResult
from app.services.fallback_service import DeepSeekFallbackService

class GeminiAnalystService:
    def __init__(self):
        # Inicializa cliente de google-genai
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.fallback_service = DeepSeekFallbackService()
        
        self.system_instruction = (
            "Eres un Analista Estadístico Deportivo Profesional. Tu objetivo es maximizar la "
            "precisión matemática hacia un 80% analizando data cruda (goles, xG, posesión, rachas, H2H). "
            "Debes estructurar tu respuesta estrictamente de acuerdo con el esquema proporcionado."
        )

    async def analyze_match(self, event_data: str) -> AIPredictionResult:
        try:
            # Usando Structured Outputs de Gemini 2.0 / 1.5 a través del SDK genai
            response = self.client.models.generate_content(
                model='gemini-2.0-flash', # O gemini-1.5-pro según disponibilidad
                contents=event_data,
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
            return await self.fallback_service.generate_prediction(event_data)

gemini_service = GeminiAnalystService()
