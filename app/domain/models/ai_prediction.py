from pydantic import BaseModel, Field
from enum import Enum

class SportEnum(str, Enum):
    football = "football"

class PredictionStatusEnum(str, Enum):
    pending = "pending"
    won = "won"
    lost = "lost"
    void = "void"

class AIPredictionResult(BaseModel):
    fixture_id: str = Field(..., description="ID del evento deportivo analizado")
    sport: SportEnum = Field(..., description="Deporte del evento")
    prediccion_mercado: str = Field(..., description="Mercado pronosticado (e.g. 'Más de 2.5 goles', 'Gana Local')")
    porcentaje_confianza: float = Field(..., description="Confianza matemática calculada por IA, idealmente cerca del 80%", ge=0.0, le=100.0)
    analisis_justificado: str = Field(..., description="Análisis fundamentado con data cruda (xG, posesión, H2H, etc.)")
    cuota_minima_recomendada: float = Field(..., description="Cuota mínima para que la apuesta tenga valor EV+", ge=1.0)

class AIPredictionRecord(AIPredictionResult):
    id: int
    status: PredictionStatusEnum = PredictionStatusEnum.pending
    actual_result: str | None = None
    
    class Config:
        from_attributes = True
