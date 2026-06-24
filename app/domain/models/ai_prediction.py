from pydantic import BaseModel, Field
from enum import Enum

class SportEnum(str, Enum):
    football = "football"

class PredictionStatusEnum(str, Enum):
    unconfirmed = "unconfirmed"
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
    is_top_match: bool = Field(False, description="Si es True, prioriza mercados seguros. Si es False, busca valor > 1.50")
    
    # HORIZONTES TEMPORALES
    apex_velocity_data: dict = Field(..., description="Data de los últimos 30 días")
    context_one_year_data: dict = Field(..., description="Estadísticas de la temporada actual")
    h2h_historic_four_years: list[H2HHistory] = Field(..., description="Enfrentamientos directos 4 años atrás")


class AIPredictionResult(BaseModel):
    fixture_id: str = Field(..., description="ID del evento deportivo analizado")
    apex_velocity_home: int = Field(..., description="Fuerza del equipo local calculada de 1 a 100", ge=1, le=100)
    apex_velocity_away: int = Field(..., description="Fuerza del equipo visitante calculada de 1 a 100", ge=1, le=100)
    prob_home: int = Field(..., description="Probabilidad base de victoria local (1-100)", ge=1, le=100)
    prob_draw: int = Field(..., description="Probabilidad base de empate (1-100)", ge=1, le=100)
    prob_away: int = Field(..., description="Probabilidad base de victoria visitante (1-100)", ge=1, le=100)
    strategy: str = Field(..., description="Categoría estratégica elegida: 'home_away', 'overs', 'corners', 'btts', 'underdog_dc'")
    selected_market: str = Field(..., description="Mercado óptimo elegido. Solo 1 mercado.")
    recommended_quota: float = Field(..., description="Cuota mínima recomendada")
    main_pick_confidence: int = Field(..., description="Porcentaje de confianza del pick principal elegido (1-100)", ge=1, le=100)
    confidence_winner: int = Field(..., description="Porcentaje de confianza para que alguien gane el partido (1-100)", ge=1, le=100)
    confidence_over: int = Field(..., description="Porcentaje de confianza para que haya Over de goles (1-100)", ge=1, le=100)
    confidence_corners: int = Field(..., description="Porcentaje de confianza para que haya un buen número de Corners (1-100)", ge=1, le=100)
    confidence_btts: int = Field(..., description="Porcentaje de confianza para que Ambos Anoten (1-100)", ge=1, le=100)
    ai_justification: str = Field(..., description="Análisis exhaustivo, nombrando a ApexTip AI y Apex Velocity")

class AIPredictionRecord(AIPredictionResult):
    id: str # UUID en base de datos
    sport: SportEnum = SportEnum.football
    league_name: str
    event_name: str
    event_date: str
    stake: float = 1.0
    tier: str = "premium"
    is_top_match: bool = False
    status: PredictionStatusEnum = PredictionStatusEnum.unconfirmed
    pnl: float | None = None
    
    class Config:
        from_attributes = True
