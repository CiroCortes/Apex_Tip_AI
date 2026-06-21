from pydantic import BaseModel, Field
from enum import Enum

class SportEnum(str, Enum):
    football = "football"

class PredictionStatusEnum(str, Enum):
    pending = "pending"
    won = "won"
    lost = "lost"
    void = "void"

class H2HHistory(BaseModel):
    date: str
    home_team: str
    away_team: str
    score: str
    corners_total: int

class TeamForm(BaseModel):
    """Métricas cortas para calcular el Apex Velocity"""
    last_5_matches_results: list[str]
    xg_average: float
    corners_average: float
    injured_key_players: int

class MatchDataPayload(BaseModel):
    fixture_id: str
    sport: SportEnum = SportEnum.football
    match_date: str
    home_team: str
    away_team: str
    current_odds: dict
    
    # HORIZONTES TEMPORALES
    apex_velocity_data: dict = Field(..., description="Data de los últimos 30 días")
    context_one_year_data: dict = Field(..., description="Estadísticas de la temporada actual")
    h2h_historic_four_years: list[H2HHistory] = Field(..., description="Enfrentamientos directos 4 años atrás")


class AIPredictionResult(BaseModel):
    fixture_id: str = Field(..., description="ID del evento deportivo analizado")
    apex_velocity_home: int = Field(..., description="Fuerza del equipo local calculada de 1 a 100", ge=1, le=100)
    apex_velocity_away: int = Field(..., description="Fuerza del equipo visitante calculada de 1 a 100", ge=1, le=100)
    selected_market: str = Field(..., description="Mercado óptimo elegido (ej. 'Corners', '1X', 'Over'). Solo 1 mercado.")
    recommended_quota: float = Field(..., description="Cuota mínima recomendada (debe ser > 1.50 para valor matemático)", ge=1.5)
    stars_confidence: int = Field(..., description="Nivel de confianza de 1 a 5 estrellas", ge=1, le=5)
    ai_justification: str = Field(..., description="Análisis masticado justificando la decisión y el filtro anti-trampa")

class AIPredictionRecord(AIPredictionResult):
    id: str # UUID en base de datos
    sport: SportEnum = SportEnum.football
    event_name: str
    event_date: str
    status: PredictionStatusEnum = PredictionStatusEnum.pending
    
    class Config:
        from_attributes = True
