from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    """
    Inicializa y retorna el cliente de Supabase utilizando las variables de entorno.
    Nota: supabase-py es sincrónico por defecto (usa HTTPX por debajo). 
    Se recomienda usar dependencias de FastAPI si se requiere control de ciclo de vida.
    """
    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_KEY
    
    if not url or not key:
        raise ValueError("Supabase credentials are not set properly.")
        
    return create_client(url, key)

supabase = get_supabase_client()
