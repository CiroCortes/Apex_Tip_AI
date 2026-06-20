from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.domain.models.ai_prediction import SportEnum

class FollowerBase(BaseModel):
    follower_id: str = Field(..., description="User UID who follows")
    followed_id: str = Field(..., description="User UID being followed")

class FollowerCreate(FollowerBase):
    pass

class PredictionPostBase(BaseModel):
    tipster_uid: str = Field(..., description="UID of the tipster creating the post")
    content: str = Field(..., description="Text content explaining the prediction", max_length=1000)
    sport: SportEnum = Field(..., description="Deporte, restringido a fútbol en el MVP")
    market: str = Field(..., max_length=100)
    recommended_odds: float = Field(..., ge=1.0)
    event_id: Optional[str] = None

class PredictionPostCreate(PredictionPostBase):
    pass

class PredictionPostResponse(PredictionPostBase):
    id: int
    created_at: datetime
    likes_count: int = 0
    
    class Config:
        from_attributes = True
