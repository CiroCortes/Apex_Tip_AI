from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "ApexTip AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # Supabase config
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Firebase config
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    
    # AI APIs
    GEMINI_API_KEY: str
    DEEPSEEK_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
