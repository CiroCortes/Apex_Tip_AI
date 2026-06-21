import httpx
from app.core.config import settings
import json

class APIFootballService:
    def __init__(self):
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-apisports-key': settings.API_FOOTBALL_KEY
        }

    async def get_fixture_stats(self, fixture_id: str) -> str:
        """
        Obtiene las estadísticas de un partido específico usando httpx asíncrono.
        Retorna la data en crudo (JSON string) para ser enviada a la IA.
        """
        if not settings.API_FOOTBALL_KEY or settings.API_FOOTBALL_KEY == "your-api-football-key":
            # Si no hay key configurada, retornamos datos simulados para que la app no crashee
            # Útil para el desarrollo sin consumir cuota
            return json.dumps({
                "fixture_id": fixture_id,
                "mock_data": True,
                "stats": {
                    "home_team": {"possession": "55%", "shots_on_target": 5},
                    "away_team": {"possession": "45%", "shots_on_target": 2}
                }
            })

        async with httpx.AsyncClient() as client:
            try:
                # Ejemplo llamando al endpoint /fixtures/statistics (asumiendo endpoint de API-Football)
                response = await client.get(
                    f"{self.base_url}/fixtures/statistics",
                    headers=self.headers,
                    params={"fixture": fixture_id}
                )
                response.raise_for_status()
                # Retornamos el JSON crudo como string para que Gemini lo lea
                return response.text
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"API-Football HTTP error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise RuntimeError(f"Failed to fetch data from API-Football: {str(e)}")

api_football_service = APIFootballService()
