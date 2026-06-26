from pydantic import BaseModel, Field
from typing import Optional

class LiveMatchPayload(BaseModel):
    fixture_id: str
    home_team: str
    away_team: str
    minute: int
    score: str = "0-0"
    shots_on_target_home: int
    shots_on_target_away: int
    corners_home: int
    corners_away: int
    dangerous_attacks_home: int = 0
    dangerous_attacks_away: int = 0
    current_odds_over_05_fh: Optional[float] = None
    current_odds_over_15_match: Optional[float] = None
    current_odds_over_05_match: Optional[float] = None
    is_top_match: bool = False

class LiveAIPredictionResult(BaseModel):
    fixture_id: str = Field(..., description="ID del evento deportivo analizado en vivo")
    strategy: str = Field(..., description="Categoría estratégica elegida: 'ht_goals' o 'over_15_match'")
    selected_market: str = Field(..., description="Mercado óptimo elegido: 'Over 0.5 Goals First Half' o 'Over 1.5 Goals Match'")
    recommended_quota: float = Field(..., description="Cuota actual capturada recomendada")
    confidence: int = Field(..., description="Porcentaje de confianza de la IA en este pick en vivo (1-100)", ge=1, le=100)
    ai_justification: str = Field(..., description="Análisis técnico de por qué este pick tiene valor basado en los remates y córners en vivo.")
