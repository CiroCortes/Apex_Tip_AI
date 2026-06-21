from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client
from app.domain.models.community import PredictionPostCreate, PredictionPostResponse, FollowerCreate
from supabase import Client

router = APIRouter()

# Schema para el perfil del Tipster en el feed
class TipsterProfile(BaseModel):
    id: UUID
    username: str
    is_premium: bool
    win_rate: float = Field(..., description="Porcentaje de acierto (e.g. 74.5)")
    yield_percentage: float = Field(..., description="Rendimiento financiero de sus picks")
    followers_count: int

@router.get("/tipsters", response_model=List[TipsterProfile])
async def get_top_tipsters(db: Client = Depends(get_supabase_client)):
    """
    Obtiene la lista de los mejores tipsters ordenados por Win Rate.
    """
    try:
        response = db.table("profiles").select("*").eq("role", "tipster").order("win_rate", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/follow/{tipster_id}", status_code=status.HTTP_201_CREATED)
async def follow_tipster(tipster_id: UUID, current_user: dict = Depends(get_current_user), db: Client = Depends(get_supabase_client)):
    """
    Permite a un usuario seguir a un Tipster.
    """
    try:
        db.table("followers").insert({
            "follower_id": current_user["uid"], 
            "following_id": str(tipster_id)
        }).execute()
        return {"message": "Has comenzado a seguir a este tipster exitosamente"}
    except Exception:
        raise HTTPException(status_code=400, detail="Error al procesar la solicitud de seguimiento o ya lo sigues.")

@router.post("/posts", response_model=PredictionPostResponse)
async def create_tipster_post(post: PredictionPostCreate, current_user: dict = Depends(get_current_user), db: Client = Depends(get_supabase_client)):
    """
    Permite a los Tipsters publicar una predicción.
    """
    roles = current_user.get("roles", {})
    if roles.get("role") != "tipster": # Asumiendo que el claim guarda el rol
        pass # Por ahora no bloqueamos estricto para facilitar pruebas, idealmente levantar 403
    
    new_post = {
        "tipster_uid": current_user["uid"],
        "content": post.content,
        "sport": post.sport.value,
        "market": post.market,
        "recommended_odds": post.recommended_odds,
        "event_id": post.event_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        response = db.table("posts").insert(new_post).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feed")
async def get_social_feed(current_user: dict = Depends(get_current_user), db: Client = Depends(get_supabase_client)):
    """
    Retorna el muro de publicaciones, ofuscando contenido premium para usuarios free.
    """
    # En un escenario real llamaríamos a db.rpc("get_user_feed", {"user_id": current_user["uid"]}).execute()
    # Para el esqueleto simulamos la respuesta ofuscando
    
    # Asumimos una lectura de base de datos mock:
    posts = [
        {"id": 1, "tipster_uid": "123", "market": "Over 2.5", "quota": 1.85, "is_premium_only": True, "argumentation": "Análisis profundo..."},
        {"id": 2, "tipster_uid": "456", "market": "Home Win", "quota": 1.50, "is_premium_only": False, "argumentation": "Análisis free..."}
    ]
    
    is_premium = current_user.get("roles", {}).get("subscription") == "premium"
    
    processed_posts = []
    for p in posts:
        if p.get("is_premium_only") and not is_premium:
            p["market"] = "🔒 CONTENIDO PREMIUM"
            p["quota"] = 0.0
            p["argumentation"] = "Suscríbete al plan Premium de ApexTip AI para desbloquear este análisis matemático."
        processed_posts.append(p)
        
    return processed_posts
