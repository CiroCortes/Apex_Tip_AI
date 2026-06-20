import json
from openai import AsyncOpenAI
from app.core.config import settings
from app.domain.models.ai_prediction import AIPredictionResult

class DeepSeekFallbackService:
    def __init__(self):
        # DeepSeek API es compatible con el protocolo de OpenAI
        self.api_key = settings.DEEPSEEK_API_KEY
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com/v1" # Ajustar a la URL real de DeepSeek
        )

    async def generate_prediction(self, raw_data: str) -> AIPredictionResult:
        if not self.api_key:
            raise ValueError("DeepSeek API Key is not configured for fallback.")

        prompt = f"""
        Actúa como un Analista Estadístico Deportivo Profesional.
        Tu objetivo es predecir resultados deportivos basándote en la siguiente data cruda:
        {raw_data}
        
        Debes responder estrictamente con un JSON que cumpla el siguiente esquema:
        {AIPredictionResult.model_json_schema()}
        """

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            # Convertir JSON text a Pydantic Model
            result_dict = json.loads(result_text)
            return AIPredictionResult(**result_dict)
            
        except Exception as e:
            raise RuntimeError(f"Fallback DeepSeek API failed: {str(e)}")
