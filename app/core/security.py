import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# Inicializar Firebase Admin SDK de forma lazy
_firebase_initialized = False

def get_firebase_app():
    global _firebase_initialized
    if not _firebase_initialized:
        if settings.FIREBASE_CREDENTIALS_PATH:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        else:
            # Use default application credentials si no se pasa archivo
            firebase_admin.initialize_app()
        _firebase_initialized = True

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Middleware/Dependency para validar JWT tokens de Firebase y extraer el UID.
    """
    # BYPASS PARA DESARROLLO LOCAL: Si no mandas token en dev, te damos un usuario de prueba
    if not credentials and settings.ENVIRONMENT == "development":
        return {
            "uid": "dev-mock-user-123",
            "email": "dev@apextip.ai",
            "roles": {"role": "tipster", "subscription": "premium"}
        }
        
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    get_firebase_app()
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        # Extraer UID y otros claims de Firebase
        user_info = {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "roles": decoded_token.get("roles", {})
        }
        return user_info
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
